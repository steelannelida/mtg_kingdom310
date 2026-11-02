#!/usr/bin/env python3
"""
Generate Forge card scripts from TNK YAML card data.

Cards with a `forge:` section in their YAML are exported.
Cards without `forge:` are skipped.

Run: python3 generate_forge.py
Then: cd forge_export && ./install.sh
"""
import os, re, yaml
from pathlib import Path

BASE         = Path("forge_export")
CARDS_DIR    = BASE / "cards"
EDITIONS_DIR = BASE / "editions"
TOKENS_DIR   = BASE / "tokens"

for d in (CARDS_DIR, EDITIONS_DIR, TOKENS_DIR):
    d.mkdir(parents=True, exist_ok=True)

RARITY = {"common": "C", "uncommon": "U", "rare": "R", "mythic": "M"}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def to_forge_mana(cost: str) -> str:
    """{2}{G}{W} → '2 G W'"""
    if not cost:
        return "no cost"
    return " ".join(re.findall(r"\{([^}]+)\}", cost))


def to_forge_types(type_line: str) -> str:
    """'Creature — Bear' → 'Creature Bear' (also handles a plain '-' typo for the em-dash)"""
    return " ".join(type_line.replace("—", " ").replace("-", " ").split())


def emit_lines(key: str, value) -> list[str]:
    """Emit one or more  KEY:value  lines, handling str or list."""
    if value is None:
        return []
    if isinstance(value, list):
        return [f"{key}:{v}" for v in value]
    return [f"{key}:{value}"]


def build_script(card: dict, face: dict | None = None) -> str:
    """
    Build a Forge card script string from a card dict.
    `face` is used for DFC back faces (pass the back_face dict merged with
    top-level card defaults as needed).
    """
    src = face if face is not None else card
    forge = src.get("forge")
    if forge is None:
        return ""

    lines = []
    lines.append(f"Name:{src['name']}")

    mana = to_forge_mana(src.get("cost", ""))
    lines.append(f"ManaCost:{mana}")

    # Colors override (needed for DFC back faces with 'no cost')
    if "colors" in (forge or {}):
        lines.append(f"Colors:{forge['colors']}")

    lines.append(f"Types:{to_forge_types(src['type_line'])}")

    p = src.get("power")
    t = src.get("toughness")
    if p is not None and t is not None:
        lines.append(f"PT:{p}/{t}")

    # DFC marker
    if "AlternateMode" in (forge or {}):
        lines.append(f"AlternateMode:{forge['AlternateMode']}")

    # Abilities from forge section
    for key in ("K", "T", "S", "A", "R"):
        lines.extend(emit_lines(key, forge.get(key)))

    # SVars
    for svar_name, svar_val in (forge.get("SVar") or {}).items():
        lines.append(f"SVar:{svar_name}:{svar_val}")

    # Oracle — single line, \n as separator (Forge format), <this> → CARDNAME
    oracle = (src.get("text") or "").replace("<this>", "CARDNAME").replace("\n", "\\n")
    lines.append(f"Oracle:{oracle}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Load all cards from YAML files
# ---------------------------------------------------------------------------

def load_all_cards() -> list[dict]:
    cards = []
    for yaml_path in sorted(Path("cards").rglob("*.yaml")):
        raw = yaml.safe_load(yaml_path.read_text())
        if not isinstance(raw, list):
            continue
        for card in raw:
            card["_source"] = str(yaml_path)
            cards.append(card)
    return cards


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    all_cards = load_all_cards()
    exported = []

    for card in all_cards:
        forge = card.get("forge")
        if forge is None:
            continue  # not scripted yet

        script = build_script(card)
        if not script:
            continue

        # Handle DFC — append ALTERNATE + back face
        back = card.get("back_face")
        if back and back.get("forge") is not None:
            back_script = build_script(card, face=back)
            script += "\n\nALTERNATE\n\n" + back_script

        slug = re.sub(r"[^a-z0-9]+", "_", card["name"].lower()).strip("_")
        out_path = CARDS_DIR / f"{slug}.txt"
        out_path.write_text(script)
        exported.append(card)
        print(f"  card: {slug}.txt  ({card.get('rarity','?')} {card.get('color','?')})")

    # --- Edition file ---
    edition_lines = []
    for i, card in enumerate(exported, 1):
        rarity_letter = RARITY.get(card.get("rarity", "common"), "C")
        edition_lines.append(f"{i} {rarity_letter} {card['name']}")

    edition = (
        "[metadata]\n"
        "Code=TNK\n"
        "Date=2026-01-01\n"
        "Name=Tridesyatoye Tzarstvo\n"
        "Type=Custom\n"
        "\n"
        "[cards]\n"
        + "\n".join(edition_lines)
        + "\n"
    )
    edition_path = EDITIONS_DIR / "Tridesyatoye Tzarstvo.txt"
    edition_path.write_text(edition)
    print(f"edition: {edition_path.name}  ({len(exported)} cards)")

    # --- Token files (static, copy as-is) ---
    tokens = {
        "w_1_1_human_peasant": (
            "Name:Human Peasant\n"
            "ManaCost:no cost\n"
            "Colors:white\n"
            "Types:Creature Human Peasant\n"
            "PT:1/1\n"
            "Token:True\n"
            "Oracle:"
        ),
    }
    for fname, content in tokens.items():
        path = TOKENS_DIR / f"{fname}.txt"
        path.write_text(content)
        print(f" token: {fname}.txt")

    # --- Install script ---
    forge_custom = os.path.expanduser("~/Library/Application Support/Forge/custom")
    install_sh = (
        "#!/bin/bash\n"
        "# Copy TNK custom files into Forge.\n"
        "set -e\n"
        f'CUSTOM="{forge_custom}"\n'
        'mkdir -p "$CUSTOM/cards" "$CUSTOM/editions" "$CUSTOM/tokens"\n'
        'cp cards/*.txt  "$CUSTOM/cards/"\n'
        'cp editions/*.txt "$CUSTOM/editions/"\n'
        'cp tokens/*.txt "$CUSTOM/tokens/"\n'
        'echo "Installed. Restart Forge to load the set."\n'
    )
    install_path = BASE / "install.sh"
    install_path.write_text(install_sh)
    install_path.chmod(0o755)

    print(f"\nDone — {len(exported)} cards exported.")
    print(f"Run:  cd forge_export && ./install.sh")


if __name__ == "__main__":
    main()
