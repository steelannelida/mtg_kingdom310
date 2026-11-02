#!/usr/bin/env python3
"""Generate per-color card frame background textures using FLUX via mflux --
same model/settings as generate_art.py uses for card art, applied to
notes.md's "Card graphic design" per-color material descriptions instead of
scene art. Output feeds render_cards.py's frame background (replacing the
procedural gradient+noise placeholder).

Usage:
    python3 generate_frame_textures.py            # all 8 themes
    python3 generate_frame_textures.py --theme red # just one
    python3 generate_frame_textures.py --force     # regenerate existing
"""

import argparse
import subprocess
from pathlib import Path

OUT_DIR = Path(__file__).parent / "templates" / "frames"

# Portrait, close to the card's 2.5:3.5 aspect ratio, both multiples of 16
WIDTH = 512
HEIGHT = 720
STEPS = 4
MODEL = "flux2-klein-4b"
QUANTIZE = "4"

SUFFIX = (
    "seamless full-bleed texture filling the entire frame edge to edge, "
    "flat even lighting, no vignette, no figures, no people, no text, "
    "no border, no logo, top-down view of the material itself"
)

# One material description per render_cards.py THEMES key, from notes.md's
# "Card graphic design" section.
THEMES = {
    "white":      "white lime plaster wall, weathered surface with subtle "
                  "cracks and trowel marks, warm off-white tone",
    "blue":       "blue water surface with gentle ripples, sunlight glinting "
                  "on small waves, deep cobalt to teal tones",
    "black":      "black dirt and peat, damp dark soil texture with clumps "
                  "of earth, deep charcoal and umber tones",
    "red":        "red granite stone surface, coarse quarried rock texture, "
                  "dark red and rust mineral flecks",
    "green":      "dense fir tree branches filling the frame with green "
                  "pine needles, dappled forest light, deep green tones",
    "land":       "cracked brown dirt of dry steppe with sparse tufts of "
                  "yellow grass, warm ochre and umber earth tones",
    "artifact":   "varnished brown wood grain, polished timber surface with "
                  "visible grain lines, warm amber wood tones",
    "multicolor": "gold leaf and scattered gemstones, ornate metallic "
                  "texture, warm gold with ruby sapphire and emerald accents",
}

SEEDS = {k: 100 + i for i, k in enumerate(THEMES)}


def generate(theme, force=False):
    out_path = OUT_DIR / f"{theme}.png"
    if out_path.exists() and not force:
        print(f"  SKIP {theme} (exists, use --force to regenerate)")
        return out_path

    prompt = f"{THEMES[theme]}, {SUFFIX}"
    print(f"[{theme}] {prompt[:90]}...")

    venv = Path(__file__).parent / ".venv" / "bin"
    cmd = [
        # invoke via the venv's python directly -- the console-script wrapper
        # hardcodes an absolute shebang path from the machine it was created
        # on and fails with "No such file or directory" otherwise
        str(venv / "python3.13"), str(venv / "mflux-generate-flux2"),
        "--model", MODEL,
        "--quantize", QUANTIZE,
        "--width", str(WIDTH),
        "--height", str(HEIGHT),
        "--steps", str(STEPS),
        "--seed", str(SEEDS[theme]),
        "--prompt", prompt,
        "--output", str(out_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"    ERROR: {result.stderr[-500:]}")
        return None
    print(f"    DONE -> {out_path}")
    return out_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--theme", choices=list(THEMES), help="Only this theme")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    themes = [args.theme] if args.theme else list(THEMES)
    for theme in themes:
        generate(theme, force=args.force)


if __name__ == "__main__":
    main()
