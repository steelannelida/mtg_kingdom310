# Forge Integration Guide — Tridesyatoye Tzarstvo

[Card-Forge/forge](https://github.com/Card-Forge/forge) is an open-source MTG engine that supports custom sets via plain-text card scripts and edition files. It can serve as a playtesting platform for TNK.

---

## Installation (macOS)

Download the latest Forge release from the [releases page](https://github.com/Card-Forge/forge/releases) and run the desktop JAR. No Homebrew or build required.

Custom set files live in:

```
~/Library/Application Support/Forge/custom/
  cards/       ← card script .txt files
  editions/    ← set definition file
  tokens/      ← token scripts (if needed)

~/Library/Caches/Forge/pics/cards/TNK/
               ← card art as "Card Name.full.jpg"
```

---

## Edition File

Create `~/Library/Application Support/Forge/custom/editions/Tridesyatoye Tzarstvo.txt`:

```
[metadata]
Code=TNK
Date=2026-01-01
Name=Tridesyatoye Tzarstvo
Type=Custom
ScryfallCode=TNK

[cards]
1  R  Ivan Tsarevich
2  U  Letopisets iz Kitezha
3  C  Domovoy
...
```

Card entry format: `<collector number> <rarity letter> <card name>` — name must exactly match the `Name:` field in the card script. An optional `@Artist Name` can follow.

Rarity letters: `C` Common, `U` Uncommon, `R` Rare, `M` Mythic, `L` Land.

---

## Card Script Format

Each card is a plain `.txt` file in `custom/cards/`. File name can be anything but conventionally matches the card name lowercased with underscores.

```
Name:Domovoy
ManaCost:1 G
Types:Creature Spirit
PT:2/1
K:Vigilance
T:Mode$ ChangesZone | Destination$ Battlefield | ValidCard$ Card.Self | Execute$ TrigETB | TriggerDescription$ When CARDNAME enters, ...
SVar:TrigETB:DB$ GainLife | Defined$ You | LifeAmount$ 2
Oracle:Vigilance\nWhen Domovoy enters, you gain 2 life.
```

### Key fields

| Field | Purpose |
|-------|---------|
| `Name:` | Card name (must match edition file exactly) |
| `ManaCost:` | Mana cost using symbols: `W U B R G`, numbers, `X`, `no cost` |
| `Colors:` | Override color identity when ManaCost alone isn't enough (e.g. back face of DFC) |
| `Types:` | Full type line space-separated: `Legendary Creature Human Wizard` |
| `PT:` | Power/toughness: `2/3` |
| `K:` | Keywords, comma-separated: `K:Flying, Haste` |
| `T:` | Triggered ability |
| `A:` | Activated ability |
| `S:` | Static ability |
| `R:` | Replacement effect |
| `SVar:` | Named sub-ability or variable |
| `Oracle:` | Oracle text (display only, `\n` for line breaks) |

### Mana symbols

`W` `U` `B` `R` `G` `C` (colorless) `X` `S` (snow) and numbers. Hybrid: `W/U`. Phyrexian: `W/P`. Generic: just a number (`2`).

---

## Double-Faced Cards (Transform)

Use `AlternateMode:DoubleFaced` on the front face, then separate faces with `ALTERNATE` on its own line. The set uses this for Tsarevna-Lyagushka, Snegurochka, Pannochka, etc.

```
Name:Snegurochka
ManaCost:2 W W
Types:Legendary Creature Human
PT:2/3
AlternateMode:DoubleFaced
T:Mode$ Phase | Phase$ Upkeep | ValidPlayer$ You | TriggerZones$ Battlefield | Execute$ TrigMelt | TriggerDescription$ At the beginning of your upkeep, if it is summer (if an opponent controls more lands than you), transform CARDNAME.
SVar:TrigMelt:DB$ SetState | Defined$ Self | Mode$ Transform | ConditionCheckSVar$ X | ConditionSVarCompare$ GE1 | SubAbility$ DBTransform
SVar:X:Count$OpponentsGreatestPermanents.Land/Minus.YouCtrl.Land
SVar:DBTransform:DB$ SetState | Defined$ Self | Mode$ Transform
Oracle:At the beginning of your upkeep, if an opponent controls more lands than you, transform Snegurochka.

ALTERNATE

Name:Rucheyek, Vesenny Potok
ManaCost:no cost
Colors:blue,green
Types:Legendary Creature Elemental
PT:4/4
K:Trample
T:Mode$ Transformed | ValidCard$ Card.Self | Execute$ TrigSpring | TriggerDescription$ Whenever CARDNAME transforms into this face, draw a card.
SVar:TrigSpring:DB$ Draw | Defined$ You | NumCards$ 1
Oracle:Trample\nWhenever this creature transforms into Rucheyek, draw a card.
```

Key transform patterns:
- **Trigger when this face is entered** (either ETB or transform): `T:Mode$ ChangesZone | Destination$ Battlefield | ...` plus `T:Mode$ Transformed | ValidCard$ Card.Self | ...` with `Secondary$ True`
- **Trigger specifically when transformed into this back face**: `T:Mode$ Transformed | ValidCard$ Card.Self | ...` (on back face only)
- **Execute transform**: `DB$ SetState | Defined$ Self | Mode$ Transform`

---

## TNK Mechanics in Forge

### Saddle (native)

Forge has built-in Saddle support. Use:

```
K:Saddle:2
```

To check if saddled in a trigger condition:

```
T:Mode$ ... | ValidCard$ Card.Self+IsSaddled | ...
```

No extra scripting required.

### Quests (Forge-native pattern)

Forge has a native `QUEST` counter type used by original Zendikar Quest enchantments. TNK Quests map naturally onto this pattern:

```
Name:Dorozhka v Kitezh (Path to Kitezh)
ManaCost:2 U
Types:Enchantment
T:Mode$ SpellCast | ValidCard$ Instant,Sorcery | ValidActivatingPlayer$ You | TriggerZones$ Battlefield | OptionalDecider$ You | Execute$ TrigCounter | TriggerDescription$ Whenever you cast an instant or sorcery spell, you may put a quest counter on CARDNAME.
SVar:TrigCounter:DB$ PutCounter | Defined$ Self | CounterType$ QUEST | CounterNum$ 1
T:Mode$ CounterAdded | CounterType$ QUEST | ValidCard$ Card.Self | CounterAmount$ GE5 | TriggerZones$ Battlefield | Execute$ TrigComplete | TriggerDescription$ When CARDNAME has five or more quest counters on it, sacrifice it and draw three cards.
SVar:TrigComplete:DB$ Sacrifice | Defined$ Self | SubAbility$ DBDraw
SVar:DBDraw:DB$ Draw | Defined$ You | NumCards$ 3
Oracle:Whenever you cast an instant or sorcery spell, you may put a quest counter on Path to Kitezh.\nWhen Path to Kitezh has five or more quest counters on it, sacrifice it and draw three cards.
```

The auto-fire-on-threshold pattern uses `T:Mode$ CounterAdded | CounterAmount$ GEn`. Alternatively, the threshold can be an activated cost like the original Quests: `A:AB$ ... | Cost$ SubCounter<5/QUEST> Sac<1/CARDNAME>`.

### Nakaz (enchantment with upfront benefit + ongoing curse)

Nakaz gives something immediately (ETB) and imposes a static or triggered penalty that punishes certain actions. Two parts:

**Upfront benefit**: ETB trigger on `ChangesZone | Destination$ Battlefield`.

**Ongoing curse**: Static ability (`S:`) or triggered ability (`T:`) that fires on the punished action.

Example pattern — draw a card when it enters, but each time you cast a non-creature spell you lose 2 life:

```
Name:Nakaz Leshego (Leshy's Decree)
ManaCost:1 G
Types:Enchantment
T:Mode$ ChangesZone | Destination$ Battlefield | ValidCard$ Card.Self | Execute$ TrigDraw | TriggerDescription$ When CARDNAME enters, draw a card.
SVar:TrigDraw:DB$ Draw | Defined$ You | NumCards$ 1
T:Mode$ SpellCast | ValidCard$ Card.nonCreature | ValidActivatingPlayer$ You | TriggerZones$ Battlefield | Execute$ TrigLoseLife | TriggerDescription$ Whenever you cast a noncreature spell, you lose 2 life.
SVar:TrigLoseLife:DB$ LoseLife | Defined$ You | LifeAmount$ 2
Oracle:When Leshy's Decree enters, draw a card.\nWhenever you cast a noncreature spell, you lose 2 life.
```

For static restrictions (e.g. "you can't cast more than one spell per turn"): use `S:Mode$ CantBeCast | NumLimitEachTurn$ 1 | ...` modeled on Curse of Exhaustion.

Nakaz can also be an Aura (Enchant creature you control) with ETB buff + triggered punish for specific behavior.

---

## Card Art

Forge looks for card images at:

```
~/Library/Caches/Forge/pics/cards/TNK/<Card Name>.full.jpg
```

The filename must exactly match the `Name:` field in the card script (spaces preserved, no URL-encoding). Format: JPEG, ~312×445 px (standard full card size) or any reasonable resolution.

A helper script can export the set's PNGs (from `art/`) into this directory with the right names:

```python
import shutil, os
from pathlib import Path
import yaml

ART_DIR = Path("art")
DEST = Path.home() / "Library/Caches/Forge/pics/cards/TNK"
DEST.mkdir(parents=True, exist_ok=True)

for yaml_path in Path("cards").rglob("*.yaml"):
    card = yaml.safe_load(yaml_path.read_text())
    for face in [card] + ([card["back_face"]] if "back_face" in card else []):
        art = ART_DIR / face.get("art_file", "")
        if art.exists():
            dest = DEST / f"{face['name']}.full.jpg"
            shutil.copy(art, dest)
            print(f"  {face['name']}")
```

Note: Forge expects JPEG. The set's art is PNG. Either convert with Pillow (`img.save(dest, 'JPEG')`) or use a Forge version that accepts PNG (some do).

---

## Tooling Script: YAML to Forge .txt

A conversion script (`export_forge.py`) would read all YAML card files and output Forge `.txt` scripts into `forge_export/cards/`. High-level structure:

1. Load each YAML
2. Parse `cost` → `ManaCost:` (convert `{W}` → `W`, `{2}` → `2`, etc.)
3. Parse `type_line` → `Types:`
4. Emit `K:` for keywords found in text (Flying, Trample, Vigilance, Haste, etc.)
5. For DFC cards, emit front + `ALTERNATE` + back
6. Write `Oracle:` from `text` (with `<this>` → `CARDNAME`)
7. Leave `T:/A:/S:` empty or templated — **abilities require manual scripting**

Ability scripting (the `T:`, `A:`, `S:`, `SVar:` lines) cannot be auto-generated from rules text and must be written by hand for each card. This is the main labor investment.

---

## Scripting Gotchas (learned from testing)

- **`SP$` spells must not include `Cost$`** — for sorceries and instants, the mana cost is handled by the `ManaCost:` field. Adding `Cost$ |` to the `A:SP$` line makes the spell cast for free.
- **`TokenAmount$` not `TokenNum$`** — the correct parameter for token quantity is `TokenAmount$`. `TokenNum$` is silently ignored and Forge creates 1 token.
- **`CantBlockSelf` does not exist** — use `Mode$ BlockRestrict | MaxBlockers$ 1` for "can't be blocked by more than one creature".
- **Oracle newlines** — use `\n` (literal backslash-n) in the `Oracle:` field, not real newlines. Real newlines cause the next line to be parsed as an unknown field.
- **Token script names are `c_a_food_sac` / `c_a_treasure_sac`**, not `food`/`treasure` — `TokenScript$ food` is silently accepted at lint/export time but resolves to nothing at runtime. Also, the token's own `Name:` is "Food Token"/"Treasure Token", not "Food"/"Treasure" — check `card.getType().hasSubtype("Food")`, not name equality.
- **`ChangeType$ Basic Land` is wrong** — the correct dot-notation is `ChangeType$ Land.Basic` (supertype.type).
- **`ConditionPresent$`/`ConditionCompare$`/`ConditionDefined$` are only honored on a chained `SubAbility$` SVar, never on the root `A:` line itself** — a root-level condition is silently ignored (not an error), which can cause an "either/or" effect to silently apply both branches. Restructure as an unconditional base effect with the bonus living on a conditioned `SubAbility$` step instead.
- **`SP$`/`AB$ Pump` silently ignores `ValidCards$`** — it only reads a single `Defined$`/`ValidTgts$` object. Any "creatures you control get +X" mass effect needs `PumpAll`, not `Pump` (confirmed against real cards Goblin War Cry / Stand or Fall for the "mass can't-block" idiom, and Radiating Lightning/Aggravate for `DamageAll`).
- **`TapAll`/`DamageAll` used with `ValidTgts$ Player`**: `ValidCards$`/`ValidCards$` should be a bare type (`Creature`), not qualified with `.TargetedPlayerCtrl` — the type filter is implicitly scoped to the targeted player already (confirmed against real cards Naya Charm and Aggravate).
- **`DB$ Sacrifice` has no `Defined$` param at all** — it reads `SacValid$` (a type filter, defaulting to `"Self"` when absent) + `Defined$ Player` (whose battlefield to filter). To sacrifice one specific *other* known card (e.g. the creature that triggered an ability), there's no direct "sacrifice this object" hook — remember it first (`RememberObjects$ TriggeredCard` on a throwaway `DB$ Pump` step), then sacrifice with `SacValid$ Card.IsRemembered | Defined$ You`, then `DB$ Cleanup | ClearRemembered$ True`.
- **"Quest" needed two fixes to work as a real Aura subtype** (RESOLVED 2026-09-25, see "Quest Subtype Fix" below for the full writeup and required install step): (1) `Quest` wasn't a subtype Forge's `CardType` recognized, so it was silently stripped from a card's actual in-game type at load time — fixed by adding `Quest:Quests` to `[EnchantmentTypes]` in Forge's own `res/lists/TypeLists.txt` (a plain data file, editable in any real Forge install, not a compiled enum). (2) `CardType.hasStringType()` checks its raw (uncapitalized) input against the subtype set *before* capitalizing for the Supertype/CoreType fallback, so a lowercase `Aura.quest` query never matched the capitalized `"Quest"` subtype actually stored on the card — fixed by capitalizing every `Aura.quest` reference to `Aura.Quest` across `cards/common/*.yaml`. **Both fixes are required together.**
- **A `DB$ DelayedTrigger`'s own remembered objects (from `RememberObjects$` on the `DelayedTrigger` line itself) live in a *separate* list from the host card's remembered list, and need a different keyword to read back later.** For a numeric amount (`SVar:X:...`): `RememberedLKI$CardX` (or plain `Remembered*`) reads the *host card's own* `getRemembered()`, which is easy to accidentally empty out before the delayed trigger ever fires if a `DB$ Cleanup | ClearRemembered$ True` step runs earlier in the same resolution chain — silently gives 0 with no error. Use `TriggerRemembered$CardX` instead (reads `sa.getTriggerRemembered()`, populated once when the delayed trigger was created, untouched by the host's own cleanup) — confirmed against the real card Rushed Rebirth. For a `ConditionDefined$`/`ConditionPresent$` check (not an amount), the equivalent is `DelayTriggerRemembered` (resolves to the object's *current* live state, empty if it's since left the zone — the right choice for "is it still there") or `DelayTriggerRememberedLKI` (the frozen snapshot instead, for the rarer case that's actually what you want). Found via live playtesting reports ("didn't lose life" from Zakladnaya Chertu, "nothing happened at end of combat" from Noch Proderzhatsa) rather than the automated suite alone — see "Known gaps" below.
- **`RememberObjects$ Triggered<X>` must name the actual `AbilityKey` a given trigger mode populates, not just whichever noun sounds right.** It resolves generically via `AbilityKey.fromString()` on whatever follows "Triggered" (e.g. `TriggeredCard` → `AbilityKey.Card`, `TriggeredBlocker` → `AbilityKey.Blocker`) — if that key was never actually set by the firing trigger (check the mode's own `Trigger*.java`'s `setTriggeringObjects()`), it silently remembers nothing, no error. A `Mode$ Blocks` trigger populates `AbilityKey.Blocker`, not `AbilityKey.Card` — `RememberObjects$ TriggeredCard` on one (Noch Proderzhatsa's original script) always remembered an empty list.

---

## Known Limitations

- **Ability scripting is manual**: Every non-trivial ability needs hand-authored Forge script. For 215 cards this is significant work. A practical approach is to script a playable subset (e.g. 60–80 cards for a constructed-style draft).
- ~~No "Quest" supertype in Forge~~ **RESOLVED (2026-09-25)**: `Quest` now works as a real Enchantment *subtype* (registered via `res/lists/TypeLists.txt`, a data file — not the compiled `Supertype` enum this note originally worried about). See "Quest Subtype Fix" below — this requires a one-time patch to every real Forge install this set is played in, not just the dev/test clone.
- **Complex replacements**: Some abilities (e.g. "put on bottom of library instead of graveyard") use replacement effects (`R:`) which can be tricky to script correctly.
- **Art format**: Forge traditionally expects JPEG. PNG may work in recent builds. Test before batch-converting.
- **Multicolor DFCs**: Back face must declare `Colors:` explicitly since `ManaCost:no cost` doesn't encode color.
- **Custom token scripts**: Tokens that are not standard (non-vanilla creature tokens) need their own script in `custom/tokens/`.

---

## Quest Subtype Fix (required install step, 2026-09-25)

Every "on a quest" cross-card check in the set (`Creature.EnchantedBy Aura.Quest`, used by ~12+ cards) depends
on `Quest` being registered as a real Forge Enchantment subtype. This is **not** part of the TNK custom-content
folder (`~/Library/Application Support/Forge/custom/`) that `install.sh` populates — it's a one-line patch to
Forge's *own* resource file, so it has to be applied to every Forge install this set is played in, including
after a Forge version upgrade (a new install = a fresh copy of this file with the patch missing again).

**How to apply**: open `res/lists/TypeLists.txt` inside the Forge installation directory (e.g.
`forge-installer-<version>/res/lists/TypeLists.txt`, sitting right next to `forge.command`/`forge.cmd` — it's a
plain text file, not bundled inside a jar) and add a `Quest:Quests` line to the `[EnchantmentTypes]` section:

```
[EnchantmentTypes]
Aura:Auras
Background
Cartouche
Case
Class
Curse:Curses
Plan:Plans
Quest:Quests
Role
Room
Rune
Saga:Sagas
Shrine:Shrines
Shard
```

Restart Forge after editing. No recompilation needed — `FModel.loadDynamicGamedata()` reads this file straight
off disk at startup (`CardType.Helper.parseTypes(...)`), the same way custom cards get picked up.

**Why this alone isn't the whole fix** — two separate bugs had to be found and fixed together (see the
Scripting Gotchas entry for the technical detail): the missing type registration (this file), *and* every card
script's `Aura.quest` needing to be capitalized to `Aura.Quest` (`CardType.hasStringType()`'s subtype check is
case-sensitive and runs before its Supertype/CoreType fallback capitalizes the query — a lowercase query never
matches the capitalized subtype string actually stored on the card). The card-script half is already fixed in
`cards/common/*.yaml` and reflected in `forge_export/`; this `TypeLists.txt` patch is the half that has to be
applied manually per Forge install.

---

## Recommended Approach

1. Start with a 40-card draft-pod subset — a couple of each color across rarities.
2. Write the edition file and card scripts for just those cards.
3. Prioritize scripting vanilla/keyword creatures (easy) and the core mechanic cards (Saddle, a few Quests, a few Nakaz).
4. Use Forge's sealed/draft mode to test limited games.
5. Expand from there card by card.

---

## Automated Card Tests (`GameSimulationTest` / Forge's test suite)

Forge ships a real TestNG test suite (JDK 17 + Maven, module `forge-gui-desktop`) that spins up an actual
`Game`/`Player`/`StaticData` and lets you place cards, cast spells, and assert on the result — no UI needed.
Crucially, its card database loader always loads `ForgeConstants.USER_CUSTOM_CARDS_DIR` (`~/Library/Application
Support/Forge/custom/cards/`) **alongside** the base set — the exact directory `forge_export/install.sh` installs
TNK's cards into. So once a card's `forge:` block is exported and installed, it can be referenced by name
(`addCard("Kalika Perekhozhiy", player)`, `CardSpecificationBuilder("Kalika Perekhozhiy")`, …) in a real test,
exactly like an official card.

TNK's example tests live in `forge_tests/java/forge/tnk/` (version-controlled with this repo) and are symlinked
into a local Forge source checkout for building:

```bash
git clone --depth=1 https://github.com/Card-Forge/forge.git forge-src   # gitignored scratch checkout
ln -s "$(pwd)/forge_tests/java/forge/tnk" forge-src/forge-gui-desktop/src/test/java/forge/tnk
cd forge_export && ./install.sh && cd ..     # (re)install TNK's cards into Forge's custom dir first
```

Requires a JDK 17+ and Maven (verified 2026-09-09 on OpenJDK 26 + Maven 3.9.16, both via Homebrew). Run every TNK
test with a filesystem-style pattern (`/`, not `.` — dotted package wildcards like `-Dtest='forge.tnk.*'` silently
match nothing):

```bash
cd forge-src
mvn -pl forge-gui-desktop -am test -Dtest='forge/tnk/**' -Dsurefire.failIfNoSpecifiedTests=false
```

(`-am` is required — running `-pl forge-gui-desktop` alone tries to resolve sibling modules from the local `.m2`
repo instead of the reactor and fails on this project's `${revision}` CI-friendly versioning.)

**All TNK tests use one style**: extend `TnkCardTestBase`, which itself extends `forge.ai.simulation.SimulationTest`
(real `FModel.initialize()`, no PowerMock) — build a `Game`, place cards, cast/activate/kill, then inspect
`Card`/`Player` state directly with TestNG asserts. Four helpers cover the shapes of test that keep coming up:

- **Static abilities / P-T / keywords** — put cards straight onto the battlefield with `addCard(...)` and read
  `Card` state directly (`getNetPower()`, `getNetToughness()`, `CombatUtil.canBlock(...)` for combat restrictions
  built via a real `Combat` object). See `TnkStaticAbilityTest`.
- **Casting a spell for real, including ETBs** — `TnkCardTestBase.castFromHand(game, player, cardName,
  basicLand, landCount)` (or the `List<String>` overload for mixed lands) puts lands on the battlefield, puts the
  card in hand, casts it via `ComputerUtil.playStack(sa, player, game)` (pays the *real* mana cost, doesn't skip
  it), resolves the spell, then calls `resolveEverything(game)` (see below) to resolve anything that triggers.
  See `TnkTriggeredAbilityTest`, `PakharTest`, `BlackCommonsTest`.
- **Activating an ability** — `TnkCardTestBase.activateAbility(game, player, source, descriptionPrefix, target)`
  finds the ability by its rendered description (which includes the cost, e.g. `"{1}{B}, {T}: Target creature
  gets -1/-1"` — the plain effect text alone won't match), optionally sets a target, pays its cost the same way,
  and resolves fully. A card placed via `addCard()` starts summoning-sick — call `card.setSickness(false)` first
  if the ability needs `{T}`. See `BlackCommonsTest`.
- **Killing a permanent to test a dies trigger** — `TnkCardTestBase.kill(game, card)`. This one has real teeth;
  see the dedicated section below before reaching for a simpler-looking alternative.

**`resolveEverything(game)`, and why `AITest.playUntilStackClear()` isn't enough**: that inherited helper breaks
out of its loop the instant the game's *phase* changes, which is too eager — a triggered ability doesn't
necessarily get flushed from Forge's internal "simultaneous triggers" holding buffer onto the real, counted stack
within the same phase it was queued in. A dies trigger queued during `MAIN1` was only actually flushed and
resolved once the game had already moved on to `COMBAT_BEGIN`. `resolveEverything` instead loops
`game.getPhaseHandler().mainLoopStep()` (with a safety cap) until both `game.getStack().isEmpty()` and
`!game.getStack().hasSimultaneousStackEntries()`, ignoring phase changes entirely. Use it (or the higher-level
helpers that call it) instead of `playUntilStackClear` for anything in this test suite.

**Killing a permanent to test a dies trigger (`kill()`) — a real trap, worth reading before touching this code.**
A dies trigger "looks back in time": by the time anything checks whether it should fire, the card is already
gone from the battlefield. Forge normally handles this automatically as part of real gameplay, but faking a death
in a test bypasses two things that real gameplay does for you, *silently* — no exception, no warning, just a card
correctly sitting in the graveyard with its trigger having quietly never fired:
1. `addCard()` puts a card straight into a zone's list, never going through the real "enters the battlefield"
   code path — so the card's triggers were never registered as *active* in the trigger handler in the first
   place. Fix: `game.getTriggerHandler().registerActiveTrigger(card, false)` before killing it.
2. The "looks back in time" re-registration that lets a *dead* card's trigger still fire lives specifically in
   `CardZoneTable.triggerChangesZoneAll()` — which is only reachable through `GameAction.checkStateEffects()`'s
   own state-based-action loop, using a `CardZoneTable` *that loop builds itself*. Calling `GameAction.destroy()`
   directly (even after `game.copyLastState()`) bypasses that table entirely: the death and its triggered ability
   both still get queued, but nothing ever re-registers the trigger as active, so it's discarded unfired. Fix:
   kill it via lethal damage instead — `card.setDamage(card.getNetToughness() + 1)` — and let
   `checkStateEffects(true)` detect, destroy, and correctly register it all as one unit, exactly like a creature
   dying to damage in a real game. `game.copyLastState()` right before the damage is still required too (that's
   the actual pre-death snapshot the "looks back in time" check reads).

Both (1) and (2) are required together — neither one alone is sufficient, and there's no error to tell you that.
`kill()` does all four steps in the right order; see its own doc comment for the one-paragraph version. This took
a lot longer to track down than it should have — if a future "whenever X dies/leaves the battlefield" test
mysteriously does nothing, re-read this section before assuming the card's script is wrong.

**Data-driven smoke test for the whole set** — `VanillaCreatureResolutionTest` doesn't hand-list cards. It reads
every exported card via `TnkCardCatalog.loadAll()` (parses `forge_export/cards/*.txt` directly — see
`-Dtnk.exportDir` if your `forge-src` checkout isn't a sibling of the repo root), keeps the ones that are
creatures with **no `T:` and no `A:` line**, computes lands from the mana cost via `ManaCostUtil.landsFor(...)`
(plain generic + single-color-letter costs only — hybrid/Phyrexian/X/snow costs return `null` and the card is
quietly excluded from the data provider, not silently passed), and feeds each as a row to a `@DataProvider` test
that casts it and asserts the resolved P/T matches what's printed. One row per card, one TestNG result per card —
scales automatically as more `forge:` blocks get added, no maintenance needed on this test itself.

*Why this is a meaningful check, not a tautology*: `K:`/`S:` lines get built into real objects the moment the
`Card` object is constructed (`Card.fromPaperCard`) — that already happens when the card enters hand, cast or
not — so a malformed keyword or static-ability string blows up regardless. `T:`/`A:` bodies are different: their
`SVar:`-referenced text is parsed **lazily**, only when the trigger actually fires or the ability is actually
activated — so a card with an untested ETB could hide a broken `SVar:` indefinitely. Restricting this data
provider to cards with neither means casting+resolving really does exercise every line in the card's `forge:`
block, not just the parts that happen to run. Cards with a `T:`/`A:` still need their own test (see
`TnkTriggeredAbilityTest`) to actually exercise that code path.

*Caught while building it (fixed 2026-09-11)*: several exported `Types:` lines read `Creature - Cat` (a literal
hyphen) instead of `Creature Cat` — `generate_forge.py`'s `to_forge_types()` only stripped the em-dash `—`, not a
plain `-`, so any card whose YAML `type_line` used a regular hyphen kept it verbatim in the export. Forge
tolerated it (an unrecognized bare token in `Types:` doesn't break card construction), so it was cosmetic rather
than a real bug, but `to_forge_types()` now strips both.

*Also caught (fixed 2026-09-11)*: Postrig's static ability was scripted as two separate `S:` lines each using
`Affected$ Creature.EnchantedBy` — not a real Forge param name for this mode. The correct pattern (confirmed
against Forge's own `Pacifism`, identical oracle text) is one combined-mode line:
`S:Mode$ CantAttack,CantBlock | ValidCard$ Creature.EnchantedBy | Description$ ...`.

**Dead end, for the record**: an earlier version of this doc recommended Forge's declarative `GameWrapper` DSL
(`forge.gamesimulationtests.*`, used to test the comprehensive rules) for anything needing a trigger to resolve.
That DSL is PowerMock-based, and on this machine's JDK 26 it compiles fine but silently executes **zero** test
methods (`Tests run: 0`, no error) — PowerMock's bytecode instrumentation doesn't play well with a JDK this new,
and `BaseGameSimulationTest`'s `@ObjectFactory` (which would normally register PowerMock's TestNG factory) is
commented out in Forge's own source. Don't spend time on that DSL here; the plain `SimulationTest`-based approach
above does everything needed (including triggers, once you know `resolveStack()` only resolves one stack object
at a time — see `TnkCardTestBase.castFromHand`'s comment) and actually runs.

**Caught by writing these tests**: Lisitsa-Khitryuga's static ability was scripted as
`Mode$ BlockRestrict | MaxBlockers$ 1`, which actually caps a *defending player's total blockers per combat*
(scoped by `ValidDefender$`, unset here — so unconditionally, for every attacker) rather than restricting how
many creatures can block *this* creature. The correct pattern, taken from Forge's own `Ironhoof Ox` (identical
oracle text), is `Mode$ MinMaxBlocker | ValidCard$ Card.Self | Max$ 1` — fixed in `cards/common/green.yaml`.
Worth double-checking any other `forge:` block that was hand-derived by analogy rather than copied from a real
Forge card with matching oracle text.

---

## All Commons Scripted (2026-09-11)

Every common card across all six `cards/common/{black,blue,red,green,white,colorless}.yaml` files (102/102) now
has a `forge:` block. All 102 export cleanly (`generate_forge.py`), lint clean (`lint_forge.py`, 2 harmless
warnings — see below), and load into Forge's card database without crashing (`mvn test` with 102 cards read).
33 of 37 automated tests pass; the 4 known failures are documented below rather than hidden.

**Method, for scaling this further**: most patterns were pulled directly from real Forge cards with matching or
near-identical oracle text (searched via `grep` across `forge-src/forge-gui/res/cardsfolder`), the same approach
that caught the Lisitsa-Khitryuga and Postrig bugs above. A few genuinely new mechanics turned up and are worth
remembering for next time:
- **Cross-card "on a quest" checks**: `Creature.EnchantedBy Aura.Quest` (or `Card.Self+EnchantedBy Aura.Quest`
  for a card checking its own status — note the capital Q) — confirmed working as of 2026-09-25, but needed two
  engine-level fixes to get there; see "Quest Subtype Fix" above for the full writeup and the required
  per-install patch step. (An earlier note here claiming this was "confirmed working" was itself a false
  positive, caught and corrected the same day the real fix landed.)
- **Bestow granting a full triggered ability** (not just a keyword/stat boost) to the enchanted creature:
  `AddTrigger$ SVarName` on the Aura's static, with `SVarName` written exactly like a normal `T:` line's params.
- **Bestow granting a static ability** to the enchanted creature (e.g. a keyword-restriction like "can't be
  blocked by more than one creature"): `AddStaticAbility$ SVarName` the same way.
- **Morbid** (a creature died this turn): `CheckSVar$ Morbid | SVar:Morbid:Count$Morbid.1.0` on a trigger, or
  `CheckSVar$ X | SVar:X:Count$Morbid.1.0` on a `Mode$ ReduceCost` static for "costs less if a creature died".
- **"If it was a creature card" after exiling/discarding from a graveyard**: `ConditionDefined$ Targeted |
  ConditionPresent$ Creature | ConditionCompare$ EQ1` on the follow-up `SubAbility`.
- **A persistent "chosen player" a later trigger can reference** (not just within one spell's resolution):
  `K:ETBReplacement:Other:ChooseP` + `SVar:ChooseP:DB$ ChoosePlayer | ...`, then `ValidPlayer$ Player.Chosen` /
  `Defined$ ChosenPlayer` in later `T:`/`SVar:` lines (see Forge's own `The Rack`).
- **A delayed "did X survive/die" check** (e.g. Quest completion needing a creature to survive combat):
  `DB$ DelayedTrigger | Mode$ Phase | Phase$ EndCombat | RememberObjects$ TriggeredCard`, then check
  `ConditionDefined$ Remembered | ConditionPresent$ Card | ConditionCompare$ EQ1` (still exists = survived) or
  `EQ0` (gone = died) on the follow-up ability.

**Known gaps** — real issues, left failing rather than papered over per explicit instruction; fix these before
trusting the affected cards in an actual game:

1. **Obman Zreniya** (`BlueCommonsTest#obmanZreniya_targetBecomesCopyOfAnotherCreature`) — the Clone effect
   doesn't apply even with correct per-sub-ability targeting (`sa.getSubAbility().getTargets().add(...)`, which
   did fix the NPE this card originally threw). Not yet root-caused.
2. **Topkoye mesto** — "activate only if that player controls a creature attacking you or a creature on a
   quest" isn't modeled at all (implemented as a plain unconditional discard-2). Restricting an *activation*
   based on properties of the target you're about to choose doesn't have an obvious Forge idiom; skipped for
   time rather than shipping a guess.

**RESOLVED (2026-09-26)**: **Den Prostoyat** and **Noch Proderzhatsa**, both found via live-play reports
("blocked and survived but nothing happened at end of combat" for both, independently). Den Prostoyat:
`OptionalDecider$` on the trigger made the *whole* trigger declinable, including the mandatory chained
`Sacrifice` — fixed by moving the "may" onto the exile's own `ChangeZone` via `TargetMin$ 0` (matching
Zakladnaya Chertu's pattern) instead of a trigger-level decision, so the sacrifice always happens regardless.
Noch Proderzhatsa: the same `ConditionDefined$ Remembered`-reads-the-host-not-the-trigger bug as Zakladnaya
Chertu (fixed to `DelayTriggerRemembered`), *plus* a second bug — `RememberObjects$ TriggeredCard` on a
`Mode$ Blocks` trigger silently remembered nothing, because that trigger mode's triggering object is keyed
`AbilityKey.Blocker`, not `AbilityKey.Card` (fixed to `RememberObjects$ TriggeredBlocker`; see the new
Scripting Gotchas entry above). Both cards' tests were also rewritten to stop depending on the AI's own block
decision (unreliable to force) in favor of firing state/trigger events directly. Suite: 111/112 passing.

**RESOLVED (2026-09-25)**: the Quest mechanic's cross-card detection — see "Quest Subtype Fix" above. This was
the root cause of 4 previously-listed failures (`RedCommonsTest#udalMolodetskaya_...`,
`QuestStateCheckTest#konnyDruzhinnnik_...`, `WhiteCommonsTest#derevenskayaDevitsa_...`,
`WhiteCommonsTest#pastva_...`), all now passing, plus `QuestStateCheckTest#okhrabrevshiyMujik_...`'s assertion
corrected (it had been a false positive). New tests added for the previously-unverified "on a quest" branches
of Bogatyrskaya Sila, Blagoslovenie, and Svetly Otrok, all passing.

**RESOLVED (2026-09-26)**: **Zakladnaya Chertu** — user reported in live play that casting it didn't reduce
their life at end of turn, matching this exact known gap. Root cause, found via the same debug-instrumentation
technique (temporarily added to `LifeLoseEffect.java`, reverted after): the script's `X: RememberedLKI$CardPower`
reads from the delayed trigger's *host card's own* remembered list — but that list gets cleared by the card's own
`DBCleanup` step immediately at cast time (right after the delayed trigger is registered), well before the
trigger actually fires at end of turn, so `X` always evaluated to 0 and no life was ever lost. Forge's
`AbilityUtils.calculateAmount()` has a *separate* mechanism for a delayed trigger's own remembered objects — the
`TriggerRemembered$` prefix, which reads `sa.getTriggerRemembered()` (the fired trigger's own private list,
populated by `RememberObjects$` back when the trigger was created, unaffected by the host card's cleanup).
Confirmed against the real card Rushed Rebirth, which uses the identical DelayedTrigger + `RememberObjects$` +
`TriggerRemembered$CardManaCost` pattern. Fixed by changing `X` to `TriggerRemembered$CardPower` in
`cards/common/black.yaml`. See "RESOLVED (2026-09-26)" below for Den Prostoyat and Noch Proderzhatsa, found and
fixed the same way, one day later.

Fixed since the 2026-09-11 write-up, likely as a side effect of a test-harness fix (see
"Automated Card Tests" below — `resolveEverything()` now unconditionally recomputes state-based actions/layers
each pass, where it previously skipped that step whenever the stack was already empty going in): Mertvets iz
Navi's Morbid-ETB graveyard-return and Kladbishchenskiy vor's conditional Treasure creation, both previously
listed as known gaps here, now pass without any card-script change.

Not touched in this pass: **uncommons and rares** (only commons were scripted), and any Quest that needs the
*counter-accumulation* pattern (`QUEST` counters, for a multi-step quest rather than a one-shot condition) —
none of the commons needed it, but some rares will (see `notes.md`'s quest list).

---

## Test Coverage Expanded to Every Color (2026-09-25)

Every common card across all six colors with a `T:`/`A:` line now has a dedicated test (previously only black
did) — `ColorlessCommonsTest`, `BlueCommonsTest`, `GreenCommonsTest`, `RedCommonsTest`, `WhiteCommonsTest`, on top
of the existing `BlackCommonsTest`/`BlackCommonsAdvancedTest`. 112 tests total, 111 passing (updated 2026-09-26
— see "Quest Subtype Fix" and the "RESOLVED" notes above); the 1 remaining failure is listed and explained in
"Known gaps" above.

**New reusable test-harness helpers** (`TnkCardTestBase`):
- `declareAttackersNaturally(game)` / `declareBlockersNaturally(game)` — advance the real phase into combat and
  let the AI naturally declare attackers/blockers. **Do not** use a manually-constructed `Combat` object
  (`new Combat(p); combat.addAttacker(...); game.getPhaseHandler().setCombat(combat);`) to test an
  attack/block-triggered ability — confirmed by direct experiment that this does NOT fire `Mode$
  Attacks`/`Mode$ Blocks` triggers through `resolveEverything()`, while natural phase progression does.
- `resolveCombatDamage(game)` — advances to `COMBAT_DAMAGE` and resolves. Needed *in addition to*
  `declareBlockersNaturally()` for anything depending on damage actually being dealt (e.g. a "deals combat
  damage to a player" trigger) — `COMBAT_DECLARE_BLOCKERS` is blockers being declared, not damage.
- `activateAbilityContaining(game, p, source, substring, target)` — like `activateAbility` but matches by a
  substring anywhere in the ability's rendered description rather than a strict prefix. Needed because a
  multi-part cost (e.g. tap + mana) doesn't reliably render in the order the card's own `Cost$` string lists it.
- `Card.tap(false, null, p)` (not `card.setTapped(true)`) is required to fire a `Mode$ Taps` trigger — like
  other raw setters used elsewhere in this suite for initial state, `setTapped()` bypasses the real event
  pipeline entirely.
- `resolveEverything()` now unconditionally calls `game.getAction().checkStateEffects(true)` on every loop
  iteration, including the first one even when the stack was already empty going in. Previously it skipped that
  entirely in that case (right after a single instant/sorcery resolves with no follow-up trigger) —
  `MagicStack.resolveStack()` itself never checks state-based actions or recomputes continuous-effect layers, so
  lethal damage from a direct-damage spell silently never destroyed its target, and a `Pump`/mass-effect result
  didn't show up in `getNetPower()`/`hasKeyword()` until something else forced a recompute.
