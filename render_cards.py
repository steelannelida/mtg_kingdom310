#!/usr/bin/env python3
"""
Card renderer: composites a full card image (frame + art + text) as SVG, for
8 sample cards (one per color/land/artifact/multicolor), per notes.md's "Card
graphic design" section.

Layout geometry (name/type/PT plates, art box, rules-text box) and text
baselines/sizes are parsed directly out of templates/template.svg at import
time -- not copied or approximated -- so edits to that file (it's meant to
be hand-tweaked in Inkscape/a text editor) take effect on the next run
without touching this script. The template's own <path> `d` strings are
reused verbatim for every shape's outline/clip; only fill colors (cream
plates, etc.) and the frame background texture are this script's own,
since the template itself is a bare geometry/typography diagram with most
shapes unfilled.

Fonts are the real Magic fonts mtg.cards itself uses (Beleren for
title/type/P-T, MPlantin for rules/flavor text) -- confirmed via their own
@font-face CSS, fetched directly from their plugin. Fan/non-commercial use
per project owner's call. Card titles render in Cyrillic (`name_ru`) since
Beleren has zero Cyrillic glyphs (confirmed by inspecting its cmap) -- title
uses PT Serif Bold instead, chosen after a side-by-side comparison of
Cyrillic-supporting candidates (see card_renders_draft/font_test/).

Frame textures are real FLUX-generated material photos (generate_frame_textures.py,
templates/frames/*.png), one per notes.md's "Card graphic design" per-color
description, with a light vignette overlay for plate-text contrast. Any
theme without a generated file yet falls back to the earlier procedural
gradient+noise placeholder.
"""
import argparse
import glob
import os
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
import yaml
from pathlib import Path

REPO = os.path.dirname(os.path.abspath(__file__))
SYMBOLS_DIR = f"{REPO}/templates/symbols"
FONTS_DIR = f"{REPO}/templates/fonts"
ART_DIR = f"{REPO}/art"
FRAMES_DIR = f"{REPO}/templates/frames"
TEMPLATE_PATH = f"{REPO}/templates/template.svg"
OUT_DIR = f"{REPO}/card_renders_draft"          # the 8-card curated preview set
OUT_DIR_ALL = f"{REPO}/card_renders"            # --all: the full card database
CARDS_DIR = f"{REPO}/cards"
FORGE_EXPORT_CARDS_DIR = f"{REPO}/forge_export/cards"
FORGE_PICS_DIR = os.path.expanduser("~/Library/Caches/Forge/pics/cards/TNK")
os.makedirs(OUT_DIR, exist_ok=True)

OUTPUT_SCALE = 2  # final raster size = template's own canvas size * this

def file_uri(path):
    """Percent-encoded file:// URI -- plain paths (esp. with spaces, as this
    repo's does) resolve under Chrome's lenient file: parser but are rejected
    by spec-correct SVG viewers (e.g. VS Code's SVG preview)."""
    return Path(path).resolve().as_uri()

# ---- fonts -----------------------------------------------------------------

def font_face_defs():
    return f'''
    @font-face {{ font-family: 'Beleren'; src: url('{file_uri(f"{FONTS_DIR}/Beleren.ttf")}'); }}
    @font-face {{ font-family: 'MPlantin'; src: url('{file_uri(f"{FONTS_DIR}/MPlantin.woff")}'); }}
    @font-face {{ font-family: 'PT Serif Title'; font-weight: 700;
      src: url('{file_uri(f"{FONTS_DIR}/PTSerif-Bold-cyrillic.woff2")}') format('woff2');
      unicode-range: U+0301, U+0400-045F, U+0490-0491, U+04B0-04B1, U+2116; }}
    @font-face {{ font-family: 'PT Serif Title'; font-weight: 700;
      src: url('{file_uri(f"{FONTS_DIR}/PTSerif-Bold-cyrillic-ext.woff2")}') format('woff2');
      unicode-range: U+0460-052F, U+1C80-1C8A, U+20B4, U+2DE0-2DFF, U+A640-A69F, U+FE2E-FE2F; }}
    @font-face {{ font-family: 'PT Serif Title'; font-weight: 700;
      src: url('{file_uri(f"{FONTS_DIR}/PTSerif-Bold-latin.woff2")}') format('woff2');
      unicode-range: U+0000-00FF, U+2000-206F; }}
    @font-face {{ font-family: 'PT Serif Title'; font-weight: 700;
      src: url('{file_uri(f"{FONTS_DIR}/PTSerif-Bold-latin-ext.woff2")}') format('woff2');
      unicode-range: U+0100-02BA, U+1E00-1E9F; }}
    '''

TITLE_FONT = "'PT Serif Title', serif"
DISPLAY_FONT = "'Beleren', 'Georgia', serif"   # type line, P/T -- always Latin
BODY_FONT = "'MPlantin', 'Georgia', serif"      # rules + flavor text -- always Latin

# ---- mana symbol sprite defs -------------------------------------------------

SYMBOL_RE = re.compile(r'viewBox="([^"]+)".*?>(.*)</svg>', re.S)

# {T} etc. don't have a same-named file in templates/symbols/ (it's TAP.svg,
# not T.svg) -- this maps a cost/rules-text token to its actual filename.
SYMBOL_FILE_ALIASES = {"T": "TAP", "Q": "UNTAP"}

def symbol_filename(token):
    return SYMBOL_FILE_ALIASES.get(token, token.replace("/", "_"))

def symbol_id(token):
    """DOM id for a token's <symbol>/<use> pair -- distinct from the on-disk
    filename since e.g. a hybrid token's '/' isn't valid in a url(#...) ref."""
    return token.replace("/", "_")

def load_symbol(token):
    path = f"{SYMBOLS_DIR}/{symbol_filename(token)}.svg"
    with open(path) as f:
        content = f.read()
    m = SYMBOL_RE.search(content)
    viewBox, inner = m.group(1), m.group(2)
    inner = inner.replace(' xmlns="http://www.w3.org/2000/svg"', '')
    return viewBox, inner.strip()

def build_symbol_defs(tokens):
    defs = []
    for tok in tokens:
        viewBox, inner = load_symbol(tok)
        defs.append(f'<symbol id="mana-{symbol_id(tok)}" viewBox="{viewBox}">{inner}</symbol>')
    return "\n".join(defs)

def parse_mana_cost(cost):
    return re.findall(r"\{([^}]+)\}", cost or "")

SYMBOL_IN_TEXT_RE = re.compile(r"\{([^}]+)\}")

def visual_len(s):
    """Approximate rendered width of a wrap_text() word, in 'character'
    units -- a {X} mana/tap token renders as a roughly one-character-wide
    icon, not its literal brace-enclosed text, so it must count as ~1 char
    for line-wrapping purposes rather than len('{W/B}')==5."""
    return len(SYMBOL_IN_TEXT_RE.sub("#", s))

def render_rules_line(x, y, line, font_family, size, style_attr):
    """Render one wrapped rules-text line, substituting {X} tokens for
    inline mana/tap icons loaded from templates/symbols/. Advances a
    running x-cursor using the same avg-char-width heuristic used for
    wrapping (size*0.52/char) -- not real glyph metrics, but consistent
    with the rest of this script's approach, which has no font-metrics
    access for the actual embedded fonts."""
    parts = SYMBOL_IN_TEXT_RE.split(line)  # text, token, text, token, ... text
    svg = ""
    cx = x
    icon = round(size * 0.8)
    gap = size * 0.12
    n = len(parts)
    for i, part in enumerate(parts):
        if i % 2 == 0:
            # the icon's own gap provides visual separation from its
            # neighbors, so trim the one literal space touching it on each
            # side rather than stacking space-character width + icon gap
            if i > 0 and part.startswith(" "):
                part = part[1:]
            if i < n - 1 and part.endswith(" "):
                part = part[:-1]
            if part:
                svg += (f'<text x="{cx:.1f}" y="{y}" font-family="{font_family}" '
                        f'font-size="{size}" style="{style_attr}">{esc(part)}</text>')
                cx += len(part) * size * 0.52
        else:
            cx += gap
            icon_y = y - icon * 0.82
            svg += f'<use href="#mana-{symbol_id(part)}" x="{cx:.1f}" y="{icon_y:.1f}" width="{icon}" height="{icon}"/>'
            cx += icon + gap
    return svg

# ---- frame texture themes (procedural placeholders -- unchanged this pass) --

THEMES = {
    "white":      {"c1": "#efe9d8", "c2": "#c9bd98", "accent": "#b9a76a"},
    "blue":       {"c1": "#3f7fae", "c2": "#0f3a5c", "accent": "#8fc7ea"},
    "black":      {"c1": "#3a332b", "c2": "#100d09", "accent": "#5c4f3a"},
    "red":        {"c1": "#a13324", "c2": "#4a120a", "accent": "#e0693f"},
    "green":      {"c1": "#3c6b3a", "c2": "#173416", "accent": "#78a15a"},
    "land":       {"c1": "#a98a57", "c2": "#5a4322", "accent": "#d8c184"},
    "artifact":   {"c1": "#8a5a34", "c2": "#4a2f18", "accent": "#c99760"},
    "multicolor": {"c1": "#d9b23c", "c2": "#7a5a10", "accent": "#f4e4a1"},
}

def frame_defs_and_fill(theme_key, uid):
    tex_path = f"{FRAMES_DIR}/{theme_key}.png"
    if os.path.exists(tex_path):
        # real FLUX-generated material texture (generate_frame_textures.py),
        # per notes.md's per-color frame descriptions -- a light vignette
        # keeps the plate text readable against the busier real texture.
        defs = f'''
        <radialGradient id="vign-{uid}" cx="50%" cy="45%" r="75%">
          <stop offset="55%" stop-color="#000000" stop-opacity="0"/>
          <stop offset="100%" stop-color="#000000" stop-opacity="0.35"/>
        </radialGradient>
        '''
        fill = f'''
        <image href="{file_uri(tex_path)}" x="0" y="0" width="{CW}" height="{CH}" preserveAspectRatio="xMidYMid slice"/>
        <rect width="{CW}" height="{CH}" fill="url(#vign-{uid})"/>
        '''
        return defs, fill

    # fallback: procedural gradient + noise placeholder, for any theme not
    # yet generated
    t = THEMES[theme_key]
    seed = abs(hash(theme_key)) % 100
    defs = f'''
    <linearGradient id="frameGrad-{uid}" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{t['c1']}"/>
      <stop offset="1" stop-color="{t['c2']}"/>
    </linearGradient>
    <filter id="tex-{uid}" x="-20%" y="-20%" width="140%" height="140%">
      <feTurbulence type="fractalNoise" baseFrequency="0.012 0.02" numOctaves="4" seed="{seed}" result="n"/>
      <feColorMatrix in="n" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0.9 0.9 0.9 0 -0.3" result="mask"/>
      <feComposite in="mask" in2="SourceGraphic" operator="in"/>
    </filter>
    '''
    fill = f'''
    <rect width="{CW}" height="{CH}" fill="url(#frameGrad-{uid})"/>
    <rect width="{CW}" height="{CH}" fill="{t['accent']}" opacity="0.35" filter="url(#tex-{uid})"/>
    '''
    return defs, fill

# ---- text helpers --------------------------------------------------------

def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def wrap_text(text, max_chars):
    words = text.split(" ")
    lines, cur = [], ""
    for w in words:
        if visual_len(cur) + visual_len(w) + 1 <= max_chars:
            cur = (cur + " " + w).strip()
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines

def fit_desc_text(text, flavor, name, box_w, box_h, base_size, base_line_h):
    """Shrink rules-text font size/leading until it fits the description
    box -- the template's literal font-size (31px on this canvas) is sized
    for a short card and overflows/truncates wordier ones (e.g. Ivan
    Tsarevich's three-ability text pushed flavor text off the card
    entirely at the fixed size)."""
    size, line_h = base_size, base_line_h
    for _ in range(8):
        max_chars = max(20, round((box_w - 24) / (size * 0.52)))
        lines = rules_lines(text, flavor, name, max_chars=max_chars)
        if len(lines) * line_h <= box_h or size <= 14:
            return lines, size, line_h
        size = max(14, round(size * 0.92))
        line_h = round(size * 1.2)
    return lines, size, line_h

def rules_lines(text, flavor, name, max_chars=44):
    lines = []
    for para in (text or "").replace("<this>", name).split("\n"):
        if para.strip():
            lines.extend(wrap_text(para.strip(), max_chars))
        else:
            lines.append("")
    if flavor:
        lines.append("")
        flines = wrap_text(flavor, max_chars)
        flines[0] = '"' + flines[0]
        flines[-1] = flines[-1] + '"'
        lines.extend(flines)
    return lines

# ---- layout: parsed directly out of templates/template.svg ----------------

NUM = r"-?\d+(?:\.\d+)?"
SVGNS = "{http://www.w3.org/2000/svg}"

def path_start(d):
    m = re.match(rf"M\s*({NUM})[\s,]+({NUM})", d)
    return float(m.group(1)), float(m.group(2))

def plate_box(d):
    """Bounds of a 'pill' shape: M x,y  h <width>  c ... <dx> <dy>  ... z --
    used by the template's name/type plates and PT box (they bulge out past
    the flat top/bottom or left/right edges via the 'c' curves, but the
    edges themselves -- which is all we need for fills/text layout -- are
    given directly by the M start point, the first 'h' length, and the
    first 'c' command's endpoint delta)."""
    x0, y0 = path_start(d)
    w = float(re.search(rf"\bh\s*({NUM})", d).group(1))
    dy = float(re.search(rf"\bc(?:\s*{NUM}){{5}}\s*({NUM})", d).group(1))
    return dict(x=x0, y=min(y0, y0 + dy), w=w, h=abs(dy))

def rect_bounds(d):
    """Bounds of an axis-aligned M/H/V/H/Z rect path (art box, frame bg,
    outer border -- no curves)."""
    x0, y0 = path_start(d)
    xs, ys, cx, cy = [x0], [y0], x0, y0
    for cmd, val in re.findall(rf"([HV])\s*({NUM})", d):
        val = float(val)
        if cmd == "H":
            cx = val
        else:
            cy = val
        xs.append(cx); ys.append(cy)
    return dict(x=min(xs), y=min(ys), w=max(xs) - min(xs), h=max(ys) - min(ys))

def connector_box(d):
    """The rules-text panel from path8112 -- an open decorative connector
    (fill:none in the template, tracing the left-margin accent line too),
    not a closed box. Its first 'h' (top edge, rightward) and first 'V'
    (right edge, downward) are the box's right/bottom edges; combined with
    the M start point (top-left) that's enough to close it into a plain
    rect for our fill/clip/text-wrap purposes."""
    x0, y0 = path_start(d)
    w = float(re.search(rf"\bh\s*({NUM})", d).group(1))
    y1 = float(re.search(rf"\bV\s*({NUM})", d).group(1))
    return dict(x=x0, y=y0, w=w, h=y1 - y0)

def load_template():
    root = ET.parse(TEMPLATE_PATH).getroot()
    tpl_w, tpl_h = float(root.get("width")), float(root.get("height"))
    paths = {el.get("id"): el.get("d") for el in root.iter(f"{SVGNS}path") if el.get("id")}
    texts = [dict(x=float(el.get("x")), y=float(el.get("y")),
                   size=float(el.get("font-size")), content=(el.text or "").strip())
             for el in root.iter(f"{SVGNS}text")]
    return tpl_w, tpl_h, paths, texts

def need_path(paths, pid):
    if pid not in paths:
        raise ValueError(f"{TEMPLATE_PATH}: missing expected <path id=\"{pid}\"> "
                          f"-- template structure changed, update render_cards.py's parsing")
    return paths[pid]

def find_text(texts, predicate, label):
    for t in texts:
        if predicate(t["content"]):
            return t
    contents = [t["content"] for t in texts]
    raise ValueError(f"{TEMPLATE_PATH}: couldn't find the {label} placeholder <text> "
                      f"among {contents} -- template structure changed, update render_cards.py's parsing")

CW, CH, TPL_PATHS, TPL_TEXTS = load_template()  # canvas size in SVG user units
W, H = round(CW * OUTPUT_SCALE), round(CH * OUTPUT_SCALE)  # final raster pixel size

BORDER_OUTER_D       = need_path(TPL_PATHS, "rect1139")
FRAME_BG_D           = need_path(TPL_PATHS, "rect1585")
ART_BOX_D            = need_path(TPL_PATHS, "rect1823")
NAME_PLATE_D         = need_path(TPL_PATHS, "path2013")
TYPE_PLATE_D         = need_path(TPL_PATHS, "path2013-0")
TEXTBOX_CONNECTOR_D  = need_path(TPL_PATHS, "path8112")
PT_BOX_D             = need_path(TPL_PATHS, "path6771")

ART        = rect_bounds(ART_BOX_D)
NAME_PLATE = plate_box(NAME_PLATE_D)
TYPE_PLATE = plate_box(TYPE_PLATE_D)
PTBOX      = plate_box(PT_BOX_D)
DESC_BOX   = connector_box(TEXTBOX_CONNECTOR_D)

TITLE_TEXT = find_text(TPL_TEXTS, lambda c: c == "Title", "title")
TYPE_TEXT  = find_text(TPL_TEXTS, lambda c: c.lower().startswith("type"), "type line")
DESC_TEXT  = find_text(TPL_TEXTS, lambda c: c == "Card text", "rules text")
PT_TEXT    = find_text(TPL_TEXTS, lambda c: bool(re.match(r"^\d+/\d+$", c)), "P/T")  # text-anchor: middle, per template.svg

NAME_SIZE = round(TITLE_TEXT["size"])
TYPE_SIZE = round(TYPE_TEXT["size"])
DESC_SIZE = round(DESC_TEXT["size"])
PT_SIZE   = round(PT_TEXT["size"])
MANA_RIGHT = NAME_PLATE["x"] + NAME_PLATE["w"] - 8


def build_card_svg(card, theme_key, art_path):
    uid = card["name"].replace(" ", "_")
    title = card.get("name_ru") or card["name"]
    type_line = card["type_line"]
    text = card.get("text", "")
    flavor = card.get("flavor_text", "")
    pt = card.get("power") is not None

    cost_syms = parse_mana_cost(card.get("cost", ""))
    inline_syms = SYMBOL_IN_TEXT_RE.findall((text or "") + " " + (flavor or ""))
    all_syms = sorted(set(cost_syms) | set(inline_syms), key=lambda s: (s.isalpha(), s))
    defs_symbols = build_symbol_defs(all_syms) if all_syms else ""

    frame_defs, frame_fill = frame_defs_and_fill(theme_key, uid)

    # --- name plate + cost ---
    pip = round(NAME_PLATE['h'] * 0.5)
    cost_svg = ""
    for i, s in enumerate(cost_syms):
        x = MANA_RIGHT - (len(cost_syms) - i) * (pip + 3)
        y = NAME_PLATE['y'] + (NAME_PLATE['h'] - pip) / 2
        cost_svg += f'<use href="#mana-{symbol_id(s)}" x="{x:.1f}" y="{y:.1f}" width="{pip}" height="{pip}"/>'

    # --- text box ---
    text_start_y = DESC_TEXT['y']
    box_w_avail = (DESC_BOX['x'] + DESC_BOX['w']) - DESC_TEXT['x'] - 10
    box_h_avail = (DESC_BOX['y'] + DESC_BOX['h'] - 5) - text_start_y
    lines, desc_size, line_h = fit_desc_text(
        text, flavor, card["name"], box_w_avail, box_h_avail, DESC_SIZE, round(DESC_SIZE * 1.2))
    text_svg = ""
    for i, line in enumerate(lines):
        y = text_start_y + i * line_h
        if y > DESC_BOX['y'] + DESC_BOX['h'] - 5:
            break
        if not line:
            continue
        style = "font-style:italic;fill:#3a3a3a;" if line.startswith('"') or (flavor and line == flavor.split("\n")[0]) else "fill:#141414;"
        text_svg += render_rules_line(DESC_TEXT["x"], y, line, BODY_FONT, desc_size, style)

    pt_svg = ""
    if pt:
        pt_svg = f'''
        <path d="{PT_BOX_D}" fill="#efe9d8" stroke="#2a2a2a" stroke-width="2"/>
        <text x="{PT_TEXT['x']}" y="{PT_TEXT['y']}" font-family="{DISPLAY_FONT}" font-size="{PT_SIZE}" font-weight="700" text-anchor="middle" fill="#141414">{card['power']}/{card['toughness']}</text>'''

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="{H}" viewBox="0 0 {CW} {CH}">
<defs>
<style>{font_face_defs()}</style>
{frame_defs}
{defs_symbols}
<clipPath id="frameclip-{uid}"><path d="{FRAME_BG_D}"/></clipPath>
<clipPath id="artclip-{uid}"><path d="{ART_BOX_D}"/></clipPath>
</defs>
<rect width="{CW}" height="{CH}" fill="#0a0a0a"/>

<!-- frame background: the real per-color texture, clipped to the template's
     own inner-border shape (rect1585) -->
<g clip-path="url(#frameclip-{uid})">
{frame_fill}
</g>

<!-- art: clipped to the template's own art-box shape (rect1823) -->
<g clip-path="url(#artclip-{uid})">
  <image href="{file_uri(art_path)}" x="{ART['x']}" y="{ART['y']}" width="{ART['w']}" height="{ART['h']}" preserveAspectRatio="xMidYMid slice"/>
</g>
<path d="{ART_BOX_D}" fill="none" stroke="#2a2a2a" stroke-width="2"/>

<!-- name plate: the template's own scalloped path2013 shape -->
<path d="{NAME_PLATE_D}" fill="#f4f0e4" stroke="#2a2a2a" stroke-width="2"/>
<text x="{TITLE_TEXT['x']}" y="{TITLE_TEXT['y']}" font-family="{TITLE_FONT}" font-size="{NAME_SIZE}" font-weight="700" fill="#141414">{esc(title)}</text>
{cost_svg}

<!-- type plate: the template's own path2013-0 shape -->
<path d="{TYPE_PLATE_D}" fill="#f4f0e4" stroke="#2a2a2a" stroke-width="2"/>
<text x="{TYPE_TEXT['x']}" y="{TYPE_TEXT['y']}" font-family="{DISPLAY_FONT}" font-size="{TYPE_SIZE}" fill="#141414">{esc(type_line)}</text>

<!-- rules-text box: path8112 in the template is an open decorative
     connector (fill:none), not a closed box; the fill rect below is
     closed from the same top/right/bottom edge coordinates it draws, and
     the connector itself is then drawn on top as the real accent line,
     including its run up the left margin past the type/art boxes -->
<rect x="{DESC_BOX['x']}" y="{DESC_BOX['y']}" width="{DESC_BOX['w']}" height="{DESC_BOX['h']}" fill="#f4f0e4" stroke="#2a2a2a" stroke-width="2"/>
{text_svg}
<path d="{TEXTBOX_CONNECTOR_D}" fill="none" stroke="#2a2a2a" stroke-width="2"/>

{pt_svg}
</svg>'''
    return svg


CARDS = [
    ("cards/common/black.yaml", "Navka", "black", "navka.png"),
    ("cards/common/blue.yaml", "Chudo-Rybka", "blue", "chudo_rybka_wonder_fish.png"),
    ("cards/common/red.yaml", "Kuznets", "red", "kuznets_smith.png"),
    ("cards/common/green.yaml", "Medved-Shatun", "green", "medved_shatun_roaming_bear.png"),
    ("cards/common/white.yaml", "Kalika Perekhozhiy", "white", "kalika_perekhozhiy_wandering_pilgrim.png"),
    ("cards/common/colorless.yaml", "Klubochek", "artifact", "klubochek_guiding_ball_of_thread.png"),
    ("cards/uncommon/lands.yaml", "Rasputye", "land", "rasputye_crossroads.png"),
    ("cards/rare/multicolor.yaml", "Ivan Tsarevich", "multicolor", "ivan_tsarevich.png"),
]

# ---- full-database rendering (--all) ---------------------------------------

def card_theme(card):
    if "Land" in card.get("type_line", ""):
        return "land"
    color = card.get("color", "colorless")
    if color == "colorless":
        return "artifact"
    if color == "multicolor":
        return "multicolor"
    return color

def iter_all_cards():
    """Yield (card_dict, source_yaml_path) for every card in cards/**/*.yaml,
    including each back_face as its own renderable 'card' -- a back face
    has no `color` key of its own, so it's given the front face's color
    dict entry directly (not just its theme) so card_theme() still works."""
    for yaml_path in sorted(glob.glob(f"{CARDS_DIR}/**/*.yaml", recursive=True)):
        if os.path.basename(yaml_path) == "manifest.yaml":
            continue
        data = yaml.safe_load(open(yaml_path)) or []
        if not isinstance(data, list):
            continue
        for card in data:
            yield card, yaml_path
            if "back_face" in card:
                back = dict(card["back_face"])
                back.setdefault("color", card.get("color"))
                yield back, yaml_path

def forge_exported_names():
    """Card names Forge will actually recognize -- parsed from
    forge_export/cards/*.txt's own Name: lines, the ground truth of what's
    currently scripted/playable (today: all commons, per CLAUDE.md)."""
    names = set()
    for path in glob.glob(f"{FORGE_EXPORT_CARDS_DIR}/*.txt"):
        for line in open(path):
            if line.startswith("Name:"):
                names.add(line[len("Name:"):].strip())
                break
    return names

# SVG <image>/@font-face need a real browser engine -- the OS thumbnailer
# (e.g. macOS QuickLook) squashes non-square canvases to a square, so
# rasterize via headless Chrome instead.
CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
]

def find_chrome():
    for path in CHROME_CANDIDATES:
        if os.path.exists(path):
            return path
    return None

def render_png(svg_path, png_path, chrome_path):
    result = subprocess.run(
        [chrome_path, "--headless", "--disable-gpu",
         f"--screenshot={png_path}", f"--window-size={W},{H}",
         f"file://{svg_path}"],
        capture_output=True, text=True,
    )
    if result.returncode != 0 or not os.path.exists(png_path):
        print(f"    PNG render FAILED for {svg_path}: {result.stderr[-300:]}")
        return False
    return True

def render_one(card, theme, art_path, out_dir, chrome_path, used_basenames):
    name = card["name"]
    base = name.replace(" ", "_")
    if base in used_basenames:
        # two different cards sharing an exact Name (a real data collision,
        # e.g. a DFC back face named identically to its own front face) --
        # don't silently clobber one render with the other
        suffix = 2
        while f"{base}_{suffix}" in used_basenames:
            suffix += 1
        print(f"  WARNING: duplicate card name {name!r} -- writing as {base}_{suffix}.* "
              f"(this will also collide in Forge's own pics/ cache; fix the name collision in the card data)")
        base = f"{base}_{suffix}"
    used_basenames.add(base)

    svg = build_card_svg(card, theme, art_path)
    out_path = f"{out_dir}/{base}.svg"
    with open(out_path, "w") as f:
        f.write(svg)

    if chrome_path:
        png_path = f"{out_dir}/{base}.png"
        if render_png(out_path, png_path, chrome_path):
            return base
        return None
    return base

def install_forge_images(out_dir):
    names = forge_exported_names()
    if not names:
        print(f"No exported cards found in {FORGE_EXPORT_CARDS_DIR} -- run generate_forge.py first.")
        return
    os.makedirs(FORGE_PICS_DIR, exist_ok=True)
    installed, missing = 0, []
    for name in sorted(names):
        src = f"{out_dir}/{name.replace(' ', '_')}.png"
        if not os.path.exists(src):
            missing.append(name)
            continue
        dest = f"{FORGE_PICS_DIR}/{name}.full.png"
        shutil.copy(src, dest)
        installed += 1
    print(f"Installed {installed}/{len(names)} Forge-exported card images to {FORGE_PICS_DIR}")
    if missing:
        print(f"  Missing renders for: {', '.join(missing)}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--svg-only", action="store_true", help="skip the PNG rasterization step")
    parser.add_argument("--all", action="store_true",
                         help="render every card in cards/**/*.yaml (incl. back faces) into card_renders/, "
                              "instead of the 8-card curated preview in card_renders_draft/")
    parser.add_argument("--install-forge", action="store_true",
                         help="after rendering, copy images for every card Forge actually has scripted "
                              "(forge_export/cards/*.txt) into Forge's local pics cache")
    args = parser.parse_args()

    chrome_path = None if args.svg_only else find_chrome()
    if not args.svg_only and not chrome_path:
        print("WARNING: no Chrome/Chromium found at the usual paths -- writing SVGs only. "
              "Edit CHROME_CANDIDATES in this script if yours lives elsewhere.")

    used_basenames = set()

    if args.all:
        os.makedirs(OUT_DIR_ALL, exist_ok=True)
        n_ok, n_fail = 0, 0
        for card, yaml_path in iter_all_cards():
            art_file = card.get("art_file")
            art_path = f"{ART_DIR}/{art_file}" if art_file else None
            if not art_path or not os.path.exists(art_path):
                print(f"  SKIP {card['name']!r} ({yaml_path}): no art at {art_path}")
                n_fail += 1
                continue
            base = render_one(card, card_theme(card), art_path, OUT_DIR_ALL, chrome_path, used_basenames)
            if base:
                n_ok += 1
            else:
                n_fail += 1
        print(f"\nRendered {n_ok} cards to {OUT_DIR_ALL} ({n_fail} skipped/failed)")
        out_dir = OUT_DIR_ALL
    else:
        for yaml_path, name, theme, art_file in CARDS:
            cards = yaml.safe_load(open(f"{REPO}/{yaml_path}"))
            card = next(c for c in cards if c["name"] == name)
            art_path = f"{ART_DIR}/{art_file}"
            base = render_one(card, theme, art_path, OUT_DIR, chrome_path, used_basenames)
            if base:
                ext = "svg+png" if chrome_path else "svg"
                print("wrote", f"{OUT_DIR}/{base}.{{{ext}}}")
        out_dir = OUT_DIR

    if args.install_forge:
        install_forge_images(out_dir)

if __name__ == "__main__":
    main()
