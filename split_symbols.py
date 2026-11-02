#!/usr/bin/env python3
"""
One-off script: splits templates/allsymbols.svg (a tiled sheet of mana/keyword
symbol glyphs, sourced from a community SVG set) into individual SVG files
under templates/symbols/, plus an index.html contact sheet for reviewing and
labeling them.

Splitting heuristic: each top-level <g> in the source file starts a new
symbol (it holds that symbol's background shape -- a plain <circle> for most,
or one/two <path> elements for notched/hybrid-split backgrounds). Any
top-level <path> elements immediately following a <g> (up to the next <g>)
are that symbol's foreground glyph. This is deterministic and loses no
content, but a handful of symbols in the source file split their background
and foreground across TWO separate <g> elements with no path directly
between them -- those come out as one background-only file followed by one
foreground-only file. Files with no visible glyph area printed as a warning
below so they're easy to spot while labeling; merge suspects by hand.
"""
import re
import xml.etree.ElementTree as ET

SRC = "templates/allsymbols.svg"
OUT_DIR = "templates/symbols"
NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", NS)

TOKEN_RE = re.compile(r"[MmLlHhVvCcSsQqTtAaZz]|-?\d*\.?\d+(?:[eE][-+]?\d+)?")

# number of numeric arguments consumed per repetition for each command letter
ARG_COUNTS = {
    "M": 2, "L": 2, "T": 2,
    "H": 1, "V": 1,
    "C": 6, "S": 4, "Q": 4,
    "A": 7,
    "Z": 0,
}


def strip_ns(tag):
    return tag.split("}")[-1]


def path_points(d):
    """Walk an SVG path 'd' string, tracking absolute position through
    relative commands, and return every anchor/control point visited in
    absolute coordinates. Good enough for a padded bounding box (arc
    commands are approximated by their endpoint, not their true curve
    extent, which is fine here since we always pad afterward)."""
    tokens = TOKEN_RE.findall(d)
    points = []
    i = 0
    cx = cy = 0.0
    start_x = start_y = 0.0
    cmd = None
    while i < len(tokens):
        tok = tokens[i]
        if tok.isalpha():
            cmd = tok
            i += 1
            continue
        if cmd is None:
            i += 1
            continue
        letter = cmd.upper()
        relative = cmd.islower()
        nargs = ARG_COUNTS[letter]
        if letter == "Z":
            cx, cy = start_x, start_y
            # after Z, an implicit new subpath starts at the same command letter
            continue
        if i + nargs > len(tokens):
            break
        vals = [float(v) for v in tokens[i:i + nargs]]
        i += nargs

        if letter in ("H", "V"):
            if letter == "H":
                nx = cx + vals[0] if relative else vals[0]
                ny = cy
            else:
                nx = cx
                ny = cy + vals[0] if relative else vals[0]
            points.append((nx, ny))
            cx, cy = nx, ny
        else:
            # all remaining commands: consume in (x,y) pairs, last pair is the new point
            pairs = [(vals[k], vals[k + 1]) for k in range(0, len(vals), 2)]
            for k, (px, py) in enumerate(pairs):
                ax = cx + px if relative else px
                ay = cy + py if relative else py
                points.append((ax, ay))
                if k == len(pairs) - 1:
                    cx, cy = ax, ay
        if letter == "M":
            start_x, start_y = cx, cy
            # subsequent implicit coordinate pairs after an M are treated as
            # L per the SVG spec -- handled for free since cmd stays "M"/"m"
    return points


def bbox_for(elements, pad_frac=0.08):
    xs, ys = [], []
    for el in elements:
        for e in [el] + list(el.iter()):
            tag = strip_ns(e.tag)
            if tag == "circle":
                cx = float(e.attrib.get("cx", 0))
                cy = float(e.attrib.get("cy", 0))
                r = float(e.attrib.get("r", 0))
                xs.extend([cx - r, cx + r])
                ys.extend([cy - r, cy + r])
            elif tag == "path" and e.attrib.get("d"):
                for px, py in path_points(e.attrib["d"]):
                    xs.append(px)
                    ys.append(py)
    if not xs or not ys:
        return None
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    w, h = x1 - x0, y1 - y0
    side = max(w, h, 1)
    pad = side * pad_frac
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    half = side / 2 + pad
    return (cx - half, cy - half, half * 2, half * 2)


def serialize(elements):
    return "".join(ET.tostring(el, encoding="unicode") for el in elements)


def main():
    tree = ET.parse(SRC)
    root = tree.getroot()
    children = list(root)

    symbols = []  # list of (elements,)
    i, n = 0, len(children)
    while i < n:
        c = children[i]
        if strip_ns(c.tag) == "g":
            group = [c]
            j = i + 1
            while j < n and strip_ns(children[j].tag) == "path":
                group.append(children[j])
                j += 1
            symbols.append(group)
            i = j
        else:
            # stray top-level path with no preceding g in this run (shouldn't
            # happen given the source file's structure, but don't drop it)
            if symbols:
                symbols[-1].append(c)
            i += 1

    print(f"Found {len(symbols)} symbols.")

    empty_glyph = []
    import os
    os.makedirs(OUT_DIR, exist_ok=True)

    thumbs = []
    for idx, elements in enumerate(symbols):
        name = f"{idx:02d}"
        bbox = bbox_for(elements)
        if bbox is None:
            bbox = (-55, -55, 110, 110)
        x, y, w, h = bbox

        has_glyph = any(strip_ns(e.tag) == "path" for e in elements[1:]) or (
            strip_ns(elements[0].tag) == "g" and any(strip_ns(gc.tag) == "path" for gc in elements[0])
        )
        if not has_glyph:
            empty_glyph.append(name)

        svg = (
            f'<svg xmlns="{NS}" viewBox="{x:.2f} {y:.2f} {w:.2f} {h:.2f}" '
            f'width="200" height="200">\n{serialize(elements)}\n</svg>\n'
        )
        with open(f"{OUT_DIR}/{name}.svg", "w") as f:
            f.write(svg)
        thumbs.append((name, x, y, w, h))

    # Contact sheet
    cells = []
    for name, x, y, w, h in thumbs:
        cells.append(
            f'<div class="cell"><img src="symbols/{name}.svg"><div class="lbl">{name}</div></div>'
        )
    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Symbol contact sheet</title>
<style>
body {{ background:#222; font-family: sans-serif; }}
.grid {{ display:grid; grid-template-columns: repeat(10, 1fr); gap: 8px; padding: 16px; }}
.cell {{ background:#333; border-radius:6px; padding:6px; text-align:center; }}
.cell img {{ width:64px; height:64px; background:#444; border-radius:50%; }}
.lbl {{ color:#ccc; font-size:12px; margin-top:4px; }}
</style></head><body>
<div class="grid">
{''.join(cells)}
</div>
</body></html>
"""
    with open(f"{OUT_DIR}/../symbols_index.html", "w") as f:
        f.write(html)

    print(f"Wrote {len(symbols)} files to {OUT_DIR}/ and templates/symbols_index.html")
    if empty_glyph:
        print("No-visible-glyph symbols (likely need merging with a neighbor):", empty_glyph)


if __name__ == "__main__":
    main()
