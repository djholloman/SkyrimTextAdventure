# Skyrim: The Chronicles of the Dragonborn

A browser-playable web edition of the existing Python text adventure. The original game engine remains in `game.py`; Flask launches one isolated Python game process per browser session and streams its `print()` output to a Nordic-inspired RPG interface.

## Run locally

Requires Python 3.10+.

```bash
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000.

## Deploy to Render

1. Push this project to your GitHub repository.
2. In Render, choose **New → Blueprint** and select the repository.
3. Render reads `render.yaml`, installs dependencies, generates a secret key, and deploys the web service.
4. Open the Render URL after deployment completes.

You can also create a Render **Web Service** manually with:
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app --workers 1 --threads 8 --timeout 120`
- Health check path: `/health`

## Project layout

- `game.py` — original Python adventure engine, retained with only a faster web-mode narration delay.
- `app.py` — Flask session/process bridge between browser input and the Python `input()` / `print()` game.
- `templates/index.html` — RPG interface structure.
- `static/style.css` — responsive Nordic fantasy styling.
- `static/game.js` — browser terminal, input, output streaming, and best-effort character HUD parsing.
- `render.yaml` — Render Blueprint configuration.

## Notes

- Each player gets a separate Python process and game state. This first release stores active sessions in the web service's memory; restarting/redeploying the service ends active games. Persistent save games and multi-instance scaling would need a database and a more structured game-state layer.
- Keep the Render service to one instance for this initial in-memory session manager. The `render.yaml` start command uses one Gunicorn worker with multiple threads.
- The browser UI polls the server for output and sends typed choices to the original game. It does not yet provide cloud saves, player accounts, or multiplayer.
- This is an unofficial fan-made project and is not affiliated with or endorsed by Bethesda.
