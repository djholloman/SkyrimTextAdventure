"""Web host for the original interactive Skyrim Python adventure.

Each browser session gets an isolated Python subprocess, so the existing
input()/print()-driven game can run without rewriting its game logic.
"""
from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from flask import Flask, jsonify, render_template, request, session

BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "local-dev-change-this-secret")
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")


@dataclass
class GameProcess:
    process: subprocess.Popen
    output: queue.Queue[str] = field(default_factory=queue.Queue)
    started_at: float = field(default_factory=time.time)
    reader: threading.Thread | None = None


GAMES: dict[str, GameProcess] = {}
GAMES_LOCK = threading.Lock()
MAX_ACTIVE_GAMES = int(os.environ.get("MAX_ACTIVE_GAMES", "40"))
GAME_TIMEOUT = int(os.environ.get("GAME_TIMEOUT_SECONDS", "7200"))


def _reader(game: GameProcess) -> None:
    """Read raw bytes so prompts without newlines reach the browser."""
    stream = game.process.stdout
    try:
        while True:
            chunk = os.read(stream.fileno(), 4096)
            if not chunk:
                break
            game.output.put(chunk.decode("utf-8", errors="replace"))
    except (OSError, ValueError):
        pass
    finally:
        game.output.put("\n\n[The adventure has ended.]\n")


def _get_game() -> tuple[str | None, GameProcess | None]:
    game_id = session.get("game_id")
    if not game_id:
        return None, None
    with GAMES_LOCK:
        game = GAMES.get(game_id)
    if game and time.time() - game.started_at > GAME_TIMEOUT:
        _stop_game(game_id)
        return game_id, None
    return game_id, game


def _stop_game(game_id: str | None) -> None:
    if not game_id:
        return
    with GAMES_LOCK:
        game = GAMES.pop(game_id, None)
    if game and game.process.poll() is None:
        game.process.terminate()
        try:
            game.process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            game.process.kill()


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/health")
def health():
    return jsonify(status="ok")


@app.post("/api/start")
def start_game():
    old_id = session.get("game_id")
    _stop_game(old_id)
    with GAMES_LOCK:
        active = sum(1 for item in GAMES.values() if item.process.poll() is None)
        if active >= MAX_ACTIVE_GAMES:
            return jsonify(error="The tavern is full. Please try again in a moment."), 503

    env = os.environ.copy()
    env["WEB_MODE"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    try:
        process = subprocess.Popen(
            [sys.executable, "-u", str(BASE_DIR / "game.py")],
            cwd=str(BASE_DIR), env=env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, bufsize=0,
        )
    except OSError as exc:
        app.logger.exception("Could not launch game")
        return jsonify(error=f"Could not start the adventure: {exc}"), 500

    game_id = uuid.uuid4().hex
    game = GameProcess(process=process)
    game.reader = threading.Thread(target=_reader, args=(game,), daemon=True)
    game.reader.start()
    with GAMES_LOCK:
        GAMES[game_id] = game
    session["game_id"] = game_id
    return jsonify(ok=True)


@app.post("/api/input")
def send_input():
    _, game = _get_game()
    if not game or game.process.poll() is not None:
        return jsonify(error="Your adventure is no longer running. Begin a new game."), 409
    data = request.get_json(silent=True) or {}
    value = data.get("value", "")
    if not isinstance(value, str) or len(value) > 500:
        return jsonify(error="Please enter a shorter response."), 400
    try:
        game.process.stdin.write((value.replace("\r", "").replace("\n", "") + "\n").encode("utf-8"))
        game.process.stdin.flush()
    except (BrokenPipeError, OSError, AttributeError):
        return jsonify(error="The game is no longer accepting input."), 409
    return jsonify(ok=True)


@app.get("/api/output")
def get_output():
    game_id, game = _get_game()
    if not game:
        return jsonify(chunks=[], running=False)
    chunks: list[str] = []
    # Bound each response to keep polling lightweight.
    for _ in range(100):
        try:
            chunks.append(game.output.get_nowait())
        except queue.Empty:
            break
    return jsonify(chunks=chunks, running=game.process.poll() is None)


@app.post("/api/restart")
def restart_game():
    _stop_game(session.get("game_id"))
    session.pop("game_id", None)
    return start_game()


@app.post("/api/leave")
def leave_game():
    _stop_game(session.get("game_id"))
    session.pop("game_id", None)
    return jsonify(ok=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
