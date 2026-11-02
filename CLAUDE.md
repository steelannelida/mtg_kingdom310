# Tridesyatoye Tzarstvo — Custom MTG Set

An unofficial Magic: The Gathering fan set (~215 cards, common/uncommon/rare) rooted in Russian and East Slavic
folklore. Set code `TNK`. Design guidelines live in `set_design_guidelines_v01.md` (written under an earlier
working title, "Tridevskoye Tsarstvo" — same set, name evolved since; that doc is the deepest source on color
philosophy, draft archetypes, and mechanics but may drift from the actual card data in `cards/`).

Full player-facing overview: `README.md`. Read that first for the pitch; this file is for how to work in the repo.

## Repo layout

- `cards/*/{white,blue,black,red,green,colorless,multicolor,lands}.yaml` — the card database, one YAML list per
  rarity/color file. `cards/manifest.yaml` lists which files are in the set.
- `viewer/` — static JS/HTML app for browsing/filtering/editing cards. Served by `server.py`.
- `art/` — generated card art (PNG). `art/previous/` holds rollback backups (gitignored).
- `art.yaml` — art style definitions used by the generators.
- `forge_export/` — generated output (Forge `.txt` card scripts + edition file), produced by `generate_forge.py`.
  Treat as build output, not source — regenerate from the YAML rather than hand-editing.
- `forge-cards` — a symlink to the local Forge install's resources, for reference. Not part of the repo content.
- `set_design_guidelines_v01.md` — deep design doc (color philosophy, 10 draft archetypes, mechanics).
- `notes.md` — scratch/working notes (card count targets, quest ideas). Informal, not authoritative.
- `templates.md` — per-color skeleton of how many creatures/removal/etc. each color should have.
- `forge_integration.md` — the reference guide for the YAML→Forge pipeline (see below).

## Card data model

Each card in a `cards/*.yaml` file is a dict with: `name` (translit), `name_ru` (Cyrillic), `name_en` (English),
`cost` (`{2}{G}` style), `type_line`, `power`/`toughness` if a creature, `text` (uses `<this>` as a
self-reference placeholder, not the literal card name), `flavor_text`, `notes`, `rarity`, `color`, `art_style`,
`art_file`, `art_prompt`, and optionally `back_face` (dict, same shape) for double-faced/transform cards.

An optional `forge:` block holds hand-authored Forge script fragments (`K:`, `A:`, `S:`, `T:`, `SVar:`) for that
card — see below. Cards without a `forge:` key are simply skipped by the exporter; `forge: {}` marks a vanilla
card (keyworded/no-ability) as intentionally reviewed with nothing to add.

## Tooling

- `python3 server.py` → viewer at `http://localhost:8642/viewer/`. Card catalog server: browse/filter/edit cards,
  trigger art generation, rollback art.
- `python3 art_server.py` → persistent FLUX (mflux) model server on port 8643 for art generation (Apple Silicon
  only). `generate_art.py` / `batch_generate.py` drive it from the CLI; `regen_list.py` regenerates a hardcoded
  list of cards pulled from `notes.md`'s "to regenerate" list; `test_styles.py` renders one card across all art
  styles for comparison.
- `migrate_names.py` — one-off migration script (translit/Cyrillic/English name splitting). Historical; check
  before rerunning against current data since it hardcodes a name lookup table.
- `generate_forge.py` — reads every card's `forge:` block and emits Forge `.txt` scripts + edition file into
  `forge_export/`. Only cards with a `forge:` key get exported.
- `lint_forge.py` — validates `forge_export/cards/*.txt` against enum values pulled from a local Forge source
  checkout: checks this repo's own `forge-src/` first, then `/tmp/forge-src`, then falls back to a bundled
  snapshot if neither exists. Run this after `generate_forge.py` and before trusting a script — it's fast and
  catches most typos long before a full Maven test cycle would.
- `.venv/` — Python venv for `mflux` (art generation). Not used by the YAML/viewer/Forge tooling.

## Forge playtesting pipeline

Goal: make the set playable in [Forge](https://github.com/Card-Forge/forge), an open-source MTG engine, for
real testing rather than just visual review in the viewer.

Flow: **hand-author `forge:` block in card YAML → `generate_forge.py` → `forge_export/` → `lint_forge.py` →
`forge_export/install.sh` copies into Forge's custom-content directory.**

Ability scripting (the actual `T:`/`A:`/`S:`/`SVar:` logic) is NOT auto-derivable from card rules text — it's
written by hand per card, referencing `forge_integration.md` for TNK-specific patterns (Quests via the native
`QUEST` counter, Nakaz as ETB-benefit + ongoing-curse, Saddle is native to Forge). That doc also has a
**Scripting Gotchas** section worth checking before writing new Forge script (e.g. `SP$` spells must omit
`Cost$`, use `TokenAmount$` not `TokenNum$`, no `CantBlockSelf` mode, `Oracle:` needs literal `\n`).

`errors.txt` is a running list of bugs found during actual Forge playtesting (e.g. a token-count mismatch) —
check it for known-bad cards before re-verifying something already flagged there.

### Automated tests

`forge_tests/java/forge/tnk/` holds TestNG tests that exercise TNK cards through Forge's real game engine (not
just a script linter). They run against a local scratch clone of Card-Forge/forge (`forge-src/`, gitignored),
symlinked in at `forge-src/forge-gui-desktop/src/test/java/forge/tnk`. Verified working (JDK 26 + Maven 3.9.16
via Homebrew): 112 tests, 111 passing, across `PakharTest`, `TnkStaticAbilityTest`, `TnkTriggeredAbilityTest`,
`VanillaCreatureResolutionTest` (data-driven — see below), `QuestStateCheckTest`, and one dedicated test file per
color with a `T:`/`A:` card (`BlackCommonsTest`+`BlackCommonsAdvancedTest`, `BlueCommonsTest`, `GreenCommonsTest`,
`RedCommonsTest`, `WhiteCommonsTest`, `ColorlessCommonsTest`) — every common card with a `T:`/`A:` line now has a
dedicated test. The 1 known-failing test is documented, not silently broken — see the "As of 2026-09-25"
section below and the tests' own comments.

**Quest mechanic requires a one-time patch to every real Forge install** (not just this dev/test clone) —
`Quest` needs registering as a real Enchantment subtype in Forge's own `res/lists/TypeLists.txt`
(`forge-installer-<version>/res/lists/TypeLists.txt`, next to `forge.command`). See `forge_integration.md`'s
"Quest Subtype Fix" section for the exact line to add and why (a second, already-fixed bug — lowercase
`Aura.quest` vs. the capitalized `Aura.Quest` actually stored — had to be fixed in `cards/common/*.yaml`
alongside it). Without this patch, every "on a quest" card in the set silently loses its quest-conditional
bonus in a real game, even though the automated tests (which patch a scratch Forge clone) all pass.

Every test extends `TnkCardTestBase` (itself `forge.ai.simulation.SimulationTest` — no PowerMock, real
`FModel.initialize()`, which loads TNK's cards from `USER_CUSTOM_CARDS_DIR` same as the real Forge app), which
provides `castFromHand(...)` (cast a card, paying its real mana cost), `activateAbility(...)` (activate a
targeted/costed ability by its rendered description), and `kill(...)` (kill a permanent to test a dies trigger —
**read its doc comment before touching it**, getting this one wrong fails silently with no error at all).
`VanillaCreatureResolutionTest` is data-driven: `TnkCardCatalog` reads `forge_export/cards/*.txt` directly and
feeds every creature with no `T:`/`A:` line (nothing left lazily-unexercised) to a `@DataProvider` test, so it
scales automatically as more `forge:` blocks get added — no per-card test needed for that category. Cards with a
`T:`/`A:` line need their own test in a file like `BlackCommonsTest`.

Run command: `-Dtest='forge/tnk/**'` (filesystem-style with `/`; the dotted `-Dtest='forge.tnk.*'` silently
matches nothing) — see `forge_integration.md`'s "Automated Card Tests" section for the full command and for two
hard-won gotchas worth reading before writing more tests: why `resolveEverything()` replaces
`AITest.playUntilStackClear()` here, and the two-part trap in testing a dies trigger. That section also documents
a dead end: Forge's declarative `GameWrapper`/PowerMock-based test DSL compiles but silently runs zero tests on
this JDK — don't reach for it.

**As of 2026-09-11**: every common card across all six `cards/common/*.yaml` files (102/102) has a `forge:`
block — all of black/blue/red/green/white/colorless commons are scripted. Nothing here is committed yet (check
`git status`).

**As of 2026-09-25**: dedicated tests now exist for every common with a `T:`/`A:` line, not just black, and the
Quest mechanic's cross-card "on a quest" detection (previously fundamentally broken — `Quest` wasn't a real
Forge type, so it was silently dropped at load, and every `Creature.EnchantedBy Aura.quest` check failed) is
now fixed — see `forge_integration.md`'s "Quest Subtype Fix" section for the two-part fix (a Forge install
patch + capitalizing `Aura.quest` to `Aura.Quest` throughout `cards/common/*.yaml`) and the required manual
step for any *other* real Forge install this set gets played in.

**As of 2026-09-26**: three more cards fixed, all found via live playtesting reports rather than the automated
suite alone (see `forge_integration.md`'s Scripting Gotchas and Known gaps for the full writeups): Zakladnaya
Chertu's delayed life-loss, Den Prostoyat's end-of-combat exile (an `OptionalDecider$` on the trigger was
wrongly making the *mandatory* sacrifice declinable too), and Noch Proderzhatsa's survive-a-block draw (two
separate "remembered objects" bugs — wrong SVar prefix, and `RememberObjects$ TriggeredCard` on a `Mode$
Blocks` trigger that actually populates `AbilityKey.Blocker`). 1 test remains known-failing, left deliberately
rather than silently skipped:
- **`BlueCommonsTest`** (1 failure): Obman Zreniya's Clone effect doesn't apply correctly even with correct
  sub-ability targeting — not yet root-caused.
- **Not modeled at all**: Topkoye mesto's "activate only if that player controls a creature attacking you or on
  a quest" restriction (implemented as an unconditional discard-2 instead — couldn't find a clean Forge idiom
  for restricting activation based on the target you're about to choose).
- Uncommons and rares are entirely unscripted still (only commons were done in this pass) — Quest counter-based
  (not just one-shot) cards, and any card needing a fresh mechanic not yet seen in commons, haven't been touched.

## Working conventions

- Card text uses `<this>` instead of repeating the card name; keep that convention when adding/editing text.
- When adding Forge scripting for a card, always run `lint_forge.py` afterward — Forge's param/enum names are
  unforgiving and easy to get subtly wrong (see Scripting Gotchas above).
- `forge_export/` is generated; regenerate it with `generate_forge.py` rather than hand-patching, so it stays in
  sync with the YAML source of truth.
- This is a from-scratch personal fan project — no CI, no test suite beyond `lint_forge.py`'s structural checks
  and manual Forge playtesting.
