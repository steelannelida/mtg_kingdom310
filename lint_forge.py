#!/usr/bin/env python3
"""
Forge card script linter for TNK.

Reads valid enum values directly from a Forge source checkout. Checks, in order:
this repo's own forge-src/ (the scratch clone used to build/run forge_tests/),
then /tmp/forge-src, then falls back to bundled snapshots if neither exists.

Usage:
    python3 lint_forge.py              # lint forge_export/cards/
    python3 lint_forge.py path/to/dir  # lint a custom directory
"""
import re, sys
from pathlib import Path

FORGE_SRC = next(
    (p for p in (Path(__file__).parent / "forge-src", Path("/tmp/forge-src")) if p.is_dir()),
    Path("/tmp/forge-src"),
)

# ---------------------------------------------------------------------------
# Extract enum values from Forge Java source
# ---------------------------------------------------------------------------

def extract_java_enum(path: Path) -> set[str]:
    """Return all enum constant names from a Java enum file."""
    text = path.read_text(errors="replace")
    # Strip line and block comments
    text = re.sub(r'//[^\n]*', '', text)
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    # Find the enum body (between first { and the first ; or method)
    m = re.search(r'enum\s+\w+[^{]*\{(.+?)(?:^\s*;|\bpublic\b|\bprivate\b|\bprotected\b|\bstatic\b)',
                  text, flags=re.DOTALL | re.MULTILINE)
    if not m:
        return set()
    body = m.group(1)
    # Enum constants: identifiers at the start of a line or after a comma,
    # followed by optional (...) or , or ;
    names = re.findall(r'\b([A-Z][A-Za-z0-9_]+)\s*(?:\(|,|\n)', body)
    return set(names)


def extract_getparam_keys(java_file: Path) -> set[str]:
    """Return all parameter names read via getParam/hasParam/getParamOrDefault."""
    text = java_file.read_text(errors="replace")
    return set(re.findall(r'(?:getParam|hasParam|getParamOrDefault)\s*\(\s*"([^"]+)"', text))


def load_forge_enums() -> dict:
    """Load all relevant enums from Forge source, or return bundled fallback."""
    if not FORGE_SRC.exists():
        print("WARNING: Forge source not found at /tmp/forge-src — using bundled fallback values.")
        print("         Clone with: git clone --depth=1 https://github.com/Card-Forge/forge.git /tmp/forge-src\n")
        return _bundled_fallback()

    game = FORGE_SRC / "forge-game/src/main/java/forge/game"

    static_modes = extract_java_enum(game / "staticability/StaticAbilityMode.java")
    trigger_modes = extract_java_enum(game / "trigger/TriggerType.java")
    api_types     = extract_java_enum(game / "ability/ApiType.java")

    # Collect every param name read by StaticAbility* implementations
    static_params = set()
    for f in (game / "staticability").glob("StaticAbility*.java"):
        static_params |= extract_getparam_keys(f)

    # Collect param names read by Trigger* implementations
    trigger_params = set()
    for f in (game / "trigger").glob("Trigger*.java"):
        trigger_params |= extract_getparam_keys(f)

    # Collect param names read by effect implementations
    effect_params = set()
    for f in (game / "ability/effects").glob("*.java"):
        effect_params |= extract_getparam_keys(f)

    print(f"Loaded from Forge source ({FORGE_SRC}):")
    print(f"  {len(static_modes)} S:Mode$ values, "
          f"{len(trigger_modes)} T:Mode$ values, "
          f"{len(api_types)} API types")
    print(f"  {len(static_params)} static params, "
          f"{len(trigger_params)} trigger params, "
          f"{len(effect_params)} effect params\n")

    return {
        "static_modes":   static_modes,
        "trigger_modes":  trigger_modes,
        "api_types":      api_types,
        "static_params":  static_params,
        "trigger_params": trigger_params,
        "effect_params":  effect_params,
    }


def _bundled_fallback() -> dict:
    """Minimal hardcoded fallback when source isn't available."""
    return {
        "static_modes": {
            "Continuous", "CantAttack", "CantBlock", "CantBlockBy", "BlockRestrict",
            "CantBlockUnless", "CantAttackUnless", "MustAttack", "MustBlock",
            "CantBeCast", "CantBeActivated", "CantPlayLand", "RaiseCost", "ReduceCost",
            "CantGainLife", "CantLoseLife", "CantTarget", "CantSacrifice", "CantExile",
            "CantDraw", "CantDiscard", "CantPutCounter", "CantRegenerate", "CantTransform",
            "CantAttach", "CantCrew", "Panharmonicon", "MinMaxBlocker", "AttackRestrict",
        },
        "trigger_modes": {
            "ChangesZone", "Phase", "Attacks", "Blocks", "AttackerBlocked",
            "DamageDone", "SpellCast", "Transformed", "CounterAdded", "CounterRemoved",
            "Dies", "DrawCard", "LifeGained", "Discarded", "Sacrificed", "Crewed", "Saddled",
        },
        "api_types": {
            "GainLife", "LoseLife", "Draw", "Discard", "PutCounter", "Token",
            "ChangeZone", "DealDamage", "Pump", "PumpAll", "Mana", "Tap", "Untap",
            "SetState", "Sacrifice", "Destroy", "Mill", "Scry", "Cleanup",
        },
        "static_params": set(),
        "trigger_params": set(),
        "effect_params": set(),
    }


# ---------------------------------------------------------------------------
# Linter
# ---------------------------------------------------------------------------

REQUIRED_FIELDS = {"Name", "ManaCost", "Types", "Oracle"}
KNOWN_KEYS = {"Name", "ManaCost", "Colors", "Types", "PT", "K", "T", "S", "A", "R",
              "SVar", "Oracle", "AlternateMode", "DeckHints", "DeckHas", "DeckNeeds",
              "AI", "SVar", "Token", "IsNonLegendary"}


def parse_pipe_params(value: str) -> dict[str, str]:
    """Parse 'Key$ Val | Key2$ Val2' into a dict."""
    params = {}
    for part in value.split("|"):
        part = part.strip()
        if "$" in part:
            k, _, v = part.partition("$")
            params[k.strip()] = v.strip()
    return params


def lint_file(path: Path, enums: dict) -> tuple[list, list]:
    errs, warns = [], []

    def err(line_no, msg):  errs.append((path.name, line_no, msg))
    def warn(line_no, msg): warns.append((path.name, line_no, msg))

    text = path.read_text()
    faces = text.split("\nALTERNATE\n")

    for face_idx, face in enumerate(faces):
        face_label = path.name if len(faces) == 1 else f"{path.name}[face{face_idx+1}]"
        lines = face.strip().splitlines()
        fields_seen = set()
        in_oracle = False

        for line_no, raw in enumerate(lines, 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                in_oracle = False
                continue
            if in_oracle:
                # Continuation of multi-line Oracle (should not happen after generator fix)
                err(line_no, f"Oracle text spills to new line (use \\n not real newline): {line!r}")
                continue

            colon = line.find(":")
            if colon == -1:
                err(line_no, f"No colon: {line!r}")
                continue

            key   = line[:colon].strip()
            value = line[colon+1:]

            if key == "Oracle":
                in_oracle = True
                fields_seen.add(key)
                continue

            fields_seen.add(key)

            if key not in KNOWN_KEYS:
                warn(line_no, f"Unrecognised field '{key}'")

            params = parse_pipe_params(value)

            # ── S: static ability ──────────────────────────────────────────
            if key == "S":
                mode = params.get("Mode")
                if mode:
                    # A static ability can combine modes as a comma-separated
                    # list (e.g. "CantAttack,CantBlock" -- see Forge's own
                    # StaticAbilityMode.smartValueOf, which splits on [, ]+).
                    modes = [m for m in re.split(r"[,\s]+", mode) if m]
                    bad_modes = [m for m in modes if m not in enums["static_modes"]]
                    if bad_modes:
                        err(line_no, f"S:Mode$ {bad_modes} not in StaticAbilityMode enum")
                    else:
                        # Check params against what this mode's class reads
                        for p in params:
                            if p in ("Mode", "Description", "Affected", "Secondary",
                                     "AffectedZone", "ActiveZones", "IsPresent",
                                     "ConditionDefined", "ConditionPresent"):
                                continue  # common shared params
                            if enums["static_params"] and p not in enums["static_params"]:
                                warn(line_no, f"S: param '{p}' not seen in any StaticAbility*.java")
                else:
                    err(line_no, "S: missing Mode$")

            # ── T: triggered ability ───────────────────────────────────────
            elif key == "T":
                mode = params.get("Mode")
                if mode:
                    if mode not in enums["trigger_modes"]:
                        err(line_no, f"T:Mode$ '{mode}' not in TriggerType enum")
                else:
                    err(line_no, "T: missing Mode$")
                if "Execute" not in params:
                    err(line_no, "T: missing Execute$")

            # ── A: activated / spell ability ───────────────────────────────
            elif key == "A":
                m = re.match(r'\s*(AB|SP|AP)\$\s*(\w+)', value)
                if m:
                    api = m.group(2)
                    if api not in enums["api_types"]:
                        err(line_no, f"A:{m.group(1)}$ effect '{api}' not in ApiType enum")
                else:
                    err(line_no, f"A: expected 'AB$' or 'SP$' prefix, got: {value[:40]!r}")

            # ── SVar ───────────────────────────────────────────────────────
            elif key == "SVar":
                parts = value.split(":", 1)
                if len(parts) == 2:
                    svar_val = parts[1].strip()
                    m = re.match(r'DB\$\s*(\w+)', svar_val)
                    if m:
                        api = m.group(1)
                        if api not in enums["api_types"]:
                            err(line_no, f"SVar DB$ effect '{api}' not in ApiType enum")
                else:
                    err(line_no, f"SVar: expected 'Name:value', got: {value!r}")

            # ── ManaCost ───────────────────────────────────────────────────
            elif key == "ManaCost":
                if value.strip() not in ("no cost", ""):
                    for sym in value.strip().split():
                        if not re.match(r'^(\d+|[WUBRGCXSQE]|[WUBRG2P]/[WUBRGP]|[WUBRG]/[WUBRGCP])$', sym):
                            warn(line_no, f"Unusual mana symbol '{sym}' — verify")

        # Required fields check (per face)
        for req in REQUIRED_FIELDS:
            if req not in fields_seen:
                err(0, f"Missing required field '{req}'")

    return errs, warns


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    cards_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("forge_export/cards")
    if not cards_dir.exists():
        print(f"Directory not found: {cards_dir}")
        print("Run generate_forge.py first, or pass a path as argument.")
        sys.exit(1)

    enums = load_forge_enums()

    card_files = sorted(cards_dir.glob("*.txt"))
    if not card_files:
        print(f"No .txt files found in {cards_dir}")
        sys.exit(1)

    print(f"Linting {len(card_files)} card scripts in {cards_dir}...\n")

    all_errs, all_warns = [], []
    for path in card_files:
        errs, warns = lint_file(path, enums)
        all_errs.extend(errs)
        all_warns.extend(warns)

    if all_warns:
        print("── Warnings (may be fine) " + "─" * 50)
        for fname, line_no, msg in all_warns:
            loc = f"{fname}:{line_no}" if line_no else fname
            print(f"  WARN  {loc}: {msg}")
        print()

    if all_errs:
        print("── Errors (will break in Forge) " + "─" * 44)
        for fname, line_no, msg in all_errs:
            loc = f"{fname}:{line_no}" if line_no else fname
            print(f"  ERR   {loc}: {msg}")
        print()
        print(f"{len(all_errs)} error(s), {len(all_warns)} warning(s).")
        sys.exit(1)
    else:
        print(f"✓ No errors. {len(all_warns)} warning(s).")


if __name__ == "__main__":
    main()
