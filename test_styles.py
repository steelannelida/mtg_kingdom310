#!/usr/bin/env python3
"""Generate the same card art in all 8 styles for comparison."""

import subprocess
import yaml
from pathlib import Path

ART_PROMPT = None  # will be read from card
CARD_FILE = "cards/common/lands.yaml"
CARD_NAME = "Rasputye"
OUT_DIR = Path("art/style_test")
STYLES_FILE = Path("art.yaml")

WIDTH = 768
HEIGHT = 512
STEPS = 4
MODEL = "flux2-klein-4b"
QUANTIZE = "4"
SEED = 42

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(STYLES_FILE) as f:
        styles = yaml.safe_load(f)

    with open(CARD_FILE) as f:
        cards = yaml.safe_load(f)

    card = next(c for c in cards if CARD_NAME.lower() in c["name"].lower())
    art_prompt = card["art_prompt"]

    print(f"Card: {card['name']}")
    print(f"Prompt: {art_prompt[:80]}...")
    print(f"Generating {len(styles)} style variants...\n")

    for style in styles:
        sid = style["id"]
        sname = style["name"]
        sprompt = style["prompt"]
        full_prompt = f"{sprompt}, {art_prompt}"
        outfile = OUT_DIR / f"style_{sid}_{sname.lower().replace(' ', '_')[:30]}.png"

        print(f"[{sid}/8] {sname}")

        cmd = [
            "mflux-generate-flux2",
            "--model", MODEL,
            "--quantize", QUANTIZE,
            "--width", str(WIDTH),
            "--height", str(HEIGHT),
            "--steps", str(STEPS),
            "--seed", str(SEED),
            "--prompt", full_prompt,
            "--output", str(outfile),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  ERROR: {result.stderr[:200]}")
        else:
            print(f"  -> {outfile}")

    print("\nDone! Check art/style_test/")

if __name__ == "__main__":
    main()
