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
- `static/*_*.png` — character badge images for each race × class combination (e.g. `nord_warrior.png`)

## Notes

- Pyodide is loaded from its official CDN, so players need an internet connection on first load.
- Save games are stored in the visitor's own browser using localStorage. They are not shared between devices or browsers.
- GitHub Pages serves static files. No secrets, API keys, or server-side Python are needed.
- This is an adaptation of the supplied console game into a browser-choice interface. The original game used synchronous `input()`/`print()` loops; the browser edition uses discrete Python game actions and choice buttons.
- The game is a fan-made text adventure and is not affiliated with or endorsed by Bethesda Softworks.

## Character badges

The sidebar and character-creation screen show a portrait badge for each race × class combination (Nord / High Elf / Khajiit × Warrior / Mage / Thief). Images live directly in `static/` (for example `static/nord_warrior.png`).

## Skills & perks

Four skills track progress: **One-Handed**, **Destruction**, **Sneak**, and **Speech**.

- Class starting bonuses: Warrior → One-Handed 25 · Mage → Destruction 25 · Thief → Sneak 25 & Speech 25
- Weapon attacks improve One-Handed; spells improve Destruction; successful escapes and sneaking improve Sneak; shop deals improve Speech
- Each level-up grants **1 perk point**
- Perks (require skill 20 + a perk point):
  - **Armsman** — +5 weapon damage
  - **Pyromancer** — +10 spell damage
  - **Shadowfoot** — +20% escape chance

Skills and unlocked perks appear in the sidebar. Spend perk points from Riverwood or the branching path menu.


## QA fixes and regression tests

The QA-tested build includes these fixes:

- Shop sales now consume one Sweetroll and pay 5 Septims; repeating the sale cannot create money.
- Successful combat retreats clear the enemy and the pending post-combat destination.
- Defeat clears active combat data.
- Invalid combat actions no longer trigger an enemy counterattack.
- Python return values are converted from Pyodide proxies into ordinary JavaScript values before rendering or saving.
- The Load button is available after the Python engine initializes, so an existing browser save can be loaded before creating a new character.

Run the included Python regression tests from the project folder:

```bash
python -m unittest discover -s tests -v
```

The tests cover character creation, shop sales, combat retreat, invalid combat actions, combat victory cleanup, and save/load round-tripping. JavaScript syntax was also checked with Node.js. The live Pyodide/browser integration should still be smoke-tested in a browser after publishing.
