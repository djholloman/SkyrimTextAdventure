# Skyrim: The Chronicles of the Dragonborn — GitHub Pages Edition

This edition runs the Python game engine in the visitor's browser using Pyodide. It uses GitHub Pages for static hosting; there is no Flask server, Render service, or backend account.

## Publish with GitHub Pages

1. Extract this ZIP.
2. Upload **the contents** of this folder to the root of your existing `SkyrimTextAdventure` repository (not the enclosing folder).
3. Commit the files to your default branch, usually `main`.
4. On GitHub, open **Settings → Pages**.
5. Under **Build and deployment**, choose **Deploy from a branch**.
6. Select branch `main` and folder `/ (root)`, then click **Save**.
7. Wait for the Pages deployment to finish. Your site will be available at:
   `https://djholloman.github.io/SkyrimTextAdventure/`

## Files

- `index.html` — game page and character creation
- `game.py` — Python game engine, executed by Pyodide
- `static/style.css` — Nordic-inspired responsive RPG styling
- `static/game.js` — browser controls and Pyodide bridge

## Notes

- Pyodide is loaded from its official CDN, so players need an internet connection on first load.
- Save games are stored in the visitor's own browser using localStorage. They are not shared between devices or browsers.
- GitHub Pages serves static files. No secrets, API keys, or server-side Python are needed.
- This is an adaptation of the supplied console game into a browser-choice interface. The original game used synchronous `input()`/`print()` loops; the browser edition uses discrete Python game actions and choice buttons.
- The game is a fan-made text adventure and is not affiliated with or endorsed by Bethesda Softworks.
