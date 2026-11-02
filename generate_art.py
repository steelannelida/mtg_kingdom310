#!/usr/bin/env python3
"""Generate card art using FLUX via mflux.

Usage:
    # Generate art for all lands:
    python generate_art.py cards/common/lands.yaml

    # Generate art for a specific card by name substring:
    python generate_art.py cards/common/lands.yaml --card "Crossroads"

    # Regenerate even if image exists:
    python generate_art.py cards/common/lands.yaml --force

    # Use a specific seed for reproducibility:
    python generate_art.py cards/common/lands.yaml --seed 42
"""

import argparse
import subprocess
import sys
import re
import yaml
from pathlib import Path

ART_DIR = Path(__file__).parent / "art"
STYLES_FILE = Path(__file__).parent / "art.yaml"

# Card art is landscape-ish to fit the art box (roughly 2:1.4 aspect)
WIDTH = 768
HEIGHT = 512
STEPS = 4  # schnell needs very few steps
MODEL = "flux2-klein-4b"
QUANTIZE = "4"  # 4-bit quantization to fit in memory comfortably

CORE_PREFIX = ""
AVOID_SUFFIX = ""


def load_styles():
    with open(STYLES_FILE) as f:
        styles = yaml.safe_load(f)
    return {s["id"]: s for s in styles}


def card_to_filename(card):
    """Use explicit art_file if set, otherwise derive from card name."""
    if card.get("art_file"):
        return card["art_file"]
    name = card["name"].lower()
    name = re.sub(r'[^a-z0-9]+', '_', name)
    name = name.strip('_')
    return name + ".png"


def generate_card_art(card, styles, seed=None, force=False):
    filename = card_to_filename(card)
    output_path = ART_DIR / filename

    if output_path.exists() and not force:
        print(f"  SKIP {filename} (exists, use --force to regenerate)")
        return output_path

    art_prompt = card.get("art_prompt")
    if not art_prompt:
        print(f"  SKIP {card['name']} (no art_prompt)")
        return None

    style_id = card.get("art_style")
    style_prompt = ""
    if style_id and style_id in styles:
        style_prompt = styles[style_id]["prompt"]

    parts = [p for p in [CORE_PREFIX, style_prompt, art_prompt, AVOID_SUFFIX] if p]
    full_prompt = ", ".join(parts)

    # Move existing file to art/previous/ so mflux doesn't append _1
    if output_path.exists():
        prev_dir = ART_DIR / "previous"
        prev_dir.mkdir(exist_ok=True)
        # Add timestamp to avoid collisions in previous/
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        prev_path = prev_dir / f"{output_path.stem}_{ts}{output_path.suffix}"
        output_path.rename(prev_path)

    print(f"  GENERATING {filename}...")
    print(f"    Style: {styles.get(style_id, {}).get('name', 'none')}")
    print(f"    Prompt: {art_prompt[:80]}...")

    cmd = [
        "mflux-generate-flux2",
        "--model", MODEL,
        "--quantize", QUANTIZE,
        "--width", str(WIDTH),
        "--height", str(HEIGHT),
        "--steps", str(STEPS),
        "--prompt", full_prompt,
        "--output", str(output_path),
    ]

    if seed is not None:
        cmd.extend(["--seed", str(seed)])

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"    ERROR: {result.stderr[:200]}")
        return None

    print(f"    DONE -> {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Generate card art via FLUX/mflux")
    parser.add_argument("yaml_file", help="YAML card file to process")
    parser.add_argument("--card", help="Only generate for cards matching this substring")
    parser.add_argument("--force", action="store_true", help="Regenerate existing images")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    args = parser.parse_args()

    ART_DIR.mkdir(exist_ok=True)

    styles = load_styles()

    with open(args.yaml_file) as f:
        cards = yaml.safe_load(f)

    if args.card:
        cards = [c for c in cards if args.card.lower() in c["name"].lower()]

    print(f"Processing {len(cards)} cards from {args.yaml_file}")

    for card in cards:
        print(f"\n[{card['name']}]")
        generate_card_art(card, styles, seed=args.seed, force=args.force)

    print("\nDone!")


if __name__ == "__main__":
    main()
