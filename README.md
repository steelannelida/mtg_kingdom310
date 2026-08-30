# Tridevskoye Tsarstvo

An unofficial Magic: The Gathering fan set rooted in Russian and East Slavic folklore — byliny, fairy tales, and pre-Christian mythology. 215 cards across common, uncommon, and rare rarities.

**Themes:** Bogatyrs and their quests · The Sea King's court · Baba Yaga's trials · Koschei's deathlessness · Forest spirits and river creatures · The Slavic calendar

**Mechanics:**
- **Quests** — Aura enchantments with completion conditions; when the quest completes, powerful effects trigger
- **Nakaz** — enchantments with an upfront benefit and an ongoing curse that punishes certain actions
- **Mounts / Saddle** — cavalry creatures that grant bonuses when ridden
- **Transform (DFC)** — characters revealed in their true form (Tsarevna-Lyagushka, Snegurochka, Pannochka…)

---

## Viewer

A local web viewer for browsing, filtering, and editing cards.

**Requirements:** Python 3

```bash
python3 server.py
# Open http://localhost:8642/viewer/
```

The viewer lets you filter by color, type, rarity, and mana value, search across all card text, and switch card names between Cyrillic · Translit · English.

---

## Art Generation

Card art is generated locally using [FLUX](https://github.com/black-forest-labs/flux) via the [mflux](https://github.com/filipstrand/mflux) library. **Requires Apple Silicon (M-series Mac).**

```bash
python3 -m venv .venv
.venv/bin/pip install mflux
.venv/bin/python art_server.py   # start the persistent generation server
```

Then use "Generate Art" in the viewer, or run `batch_generate.py` to generate all missing images at once.

Art prompts are stored in each card's YAML and can be edited in the viewer.

---

## Card Data

All cards live in `cards/`, organized by rarity and color:

```
cards/
  common/   black  blue  colorless  green  red  white
  uncommon/ black  blue  colorless  green  lands  multicolor  red  white
  rare/     black  blue  colorless  green  lands  multicolor  red  white
```

Each card has fields: `name` (translit), `name_ru` (Cyrillic), `name_en` (English), `cost`, `type_line`, `text`, `flavor_text`, `art_file`, `art_prompt`, `art_style`, and optionally `back_face` for double-faced cards.

---

## License

Card designs, code, and written content: [CC BY-NC-SA 4.0](LICENSE)

AI-generated artwork (`art/`): produced with FLUX; AI-generated images carry no copyright.

*Magic: The Gathering is © Wizards of the Coast LLC. This is an unofficial fan project made under the [WotC Fan Content Policy](https://company.wizards.com/en/legal/fancontentpolicy), not affiliated with or endorsed by Wizards of the Coast.*
