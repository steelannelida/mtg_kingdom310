#!/usr/bin/env python3
"""Card catalog server with editing, art generation, and rollback."""

import json
import os
import re
import subprocess
import threading
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import yaml

ROOT = Path(__file__).parent
CARDS_DIR = ROOT / "cards"
ART_DIR = ROOT / "art"
PREV_DIR = ART_DIR / "previous"
STYLES_FILE = ROOT / "art.yaml"

# Track generation status
gen_status = {}  # art_file -> {"status": "running"|"done"|"error", "message": "..."}
gen_lock = threading.Lock()  # Only one generation at a time


def load_styles():
    with open(STYLES_FILE) as f:
        styles = yaml.safe_load(f)
    return {s["id"]: s for s in styles}


def find_card_in_file(yaml_path, card_name):
    """Find a card by name in a YAML file, return (cards_list, index)."""
    with open(yaml_path) as f:
        cards = yaml.safe_load(f)
    for i, card in enumerate(cards):
        if card["name"] == card_name:
            return cards, i
    return cards, -1


def save_cards(yaml_path, cards):
    """Write cards list back to YAML, preserving human-readable style."""
    # Use block style for multiline strings, keep it readable
    class CustomDumper(yaml.SafeDumper):
        pass

    def str_representer(dumper, data):
        if '\n' in data:
            return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
        if any(c in data for c in ':{}[],"\'#&*!|>%@`'):
            return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='"')
        return dumper.represent_scalar('tag:yaml.org,2002:str', data)

    CustomDumper.add_representer(str, str_representer)

    with open(yaml_path, 'w') as f:
        yaml.dump(cards, f, Dumper=CustomDumper, default_flow_style=False,
                  allow_unicode=True, sort_keys=False, width=200)


ART_SERVER = "http://127.0.0.1:8643"


def generate_art_async(card, yaml_path):
    """Send generation request to the persistent art server."""
    art_file = card.get("art_file", "")
    if not art_file:
        gen_status[art_file] = {"status": "error", "message": "No art_file set"}
        return

    gen_status[art_file] = {"status": "running", "message": "Generating..."}

    try:
        import urllib.request
        req = urllib.request.Request(
            f"{ART_SERVER}/generate",
            data=json.dumps({
                "art_file": art_file,
                "art_prompt": card.get("art_prompt", ""),
                "art_style": card.get("art_style"),
                "seed": 42,
            }).encode(),
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=300)
        result = json.loads(resp.read())
        if result.get("ok"):
            gen_status[art_file] = {"status": "done", "message": "Generated successfully"}
        else:
            gen_status[art_file] = {"status": "error", "message": result.get("error", "Unknown error")}
    except Exception as e:
        gen_status[art_file] = {"status": "error", "message": str(e)}


def list_previous_art(art_file):
    """List previous versions of an art file."""
    if not art_file:
        return []
    stem = Path(art_file).stem
    versions = []
    if PREV_DIR.exists():
        for f in sorted(PREV_DIR.glob(f"{stem}_*.png"), reverse=True):
            versions.append({
                "filename": f.name,
                "path": f"art/previous/{f.name}",
                "timestamp": f.stat().st_mtime,
            })
    return versions


class CardServer(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/previous-art":
            params = parse_qs(parsed.query)
            art_file = params.get("file", [""])[0]
            versions = list_previous_art(art_file)
            self._json_response(versions)

        elif path == "/api/gen-status":
            params = parse_qs(parsed.query)
            art_file = params.get("file", [""])[0]
            status = gen_status.get(art_file, {"status": "idle"})
            self._json_response(status)

        elif path == "/":
            self.send_response(302)
            self.send_header("Location", "/viewer/")
            self.end_headers()

        else:
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len)

        if path == "/api/save-card":
            try:
                data = json.loads(body)
                source = data["source"]  # e.g. "common/white.yaml"
                card_name = data["original_name"]
                updates = data["updates"]

                yaml_path = CARDS_DIR / source
                cards, idx = find_card_in_file(yaml_path, card_name)
                if idx == -1:
                    self._json_response({"error": f"Card '{card_name}' not found"}, 404)
                    return

                # Apply updates
                for key, value in updates.items():
                    if key.startswith("back_face."):
                        bf_key = key[len("back_face."):]
                        if "back_face" not in cards[idx]:
                            cards[idx]["back_face"] = {}
                        if value == "" and bf_key == "art_style":
                            cards[idx]["back_face"].pop(bf_key, None)
                        elif bf_key == "art_style":
                            try:
                                cards[idx]["back_face"][bf_key] = int(value)
                            except ValueError:
                                cards[idx]["back_face"][bf_key] = value
                        else:
                            cards[idx]["back_face"][bf_key] = value
                    elif value == "" and key in ("power", "toughness", "art_style"):
                        cards[idx].pop(key, None)
                    elif key in ("power", "toughness"):
                        try:
                            cards[idx][key] = int(value)
                        except ValueError:
                            cards[idx][key] = value
                    elif key == "art_style":
                        try:
                            cards[idx][key] = int(value)
                        except ValueError:
                            cards[idx][key] = value
                    else:
                        cards[idx][key] = value

                save_cards(yaml_path, cards)
                self._json_response({"ok": True, "card": cards[idx]})
            except Exception as e:
                self._json_response({"error": str(e)}, 500)

        elif path == "/api/generate-art":
            try:
                data = json.loads(body)
                source = data["source"]
                card_name = data["card_name"]

                yaml_path = CARDS_DIR / source
                cards, idx = find_card_in_file(yaml_path, card_name)
                if idx == -1:
                    self._json_response({"error": f"Card '{card_name}' not found"}, 404)
                    return

                card = cards[idx]
                use_back_face = data.get("back_face", False)

                if use_back_face:
                    face = card.setdefault("back_face", {})
                    if not face.get("art_file"):
                        name = face.get("name", card["name"]).lower()
                        name = re.sub(r'[^a-z0-9]+', '_', name).strip('_')
                        face["art_file"] = name + ".png"
                        save_cards(yaml_path, cards)
                else:
                    face = card
                    if not face.get("art_file"):
                        name = face["name"].lower()
                        name = re.sub(r'[^a-z0-9]+', '_', name).strip('_')
                        face["art_file"] = name + ".png"
                        cards[idx] = face
                        save_cards(yaml_path, cards)

                thread = threading.Thread(target=generate_art_async, args=(face, yaml_path))
                thread.start()
                self._json_response({"ok": True, "message": "Generation started", "art_file": face["art_file"]})
            except Exception as e:
                self._json_response({"error": str(e)}, 500)

        elif path == "/api/restore-art":
            try:
                data = json.loads(body)
                prev_file = data["previous_file"]  # filename in previous/
                art_file = data["art_file"]  # current art_file

                prev_path = PREV_DIR / prev_file
                current_path = ART_DIR / art_file

                if not prev_path.exists():
                    self._json_response({"error": "Previous file not found"}, 404)
                    return

                # Move current to previous
                if current_path.exists():
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    backup = PREV_DIR / f"{current_path.stem}_{ts}{current_path.suffix}"
                    current_path.rename(backup)

                # Copy previous to current (keep the previous copy too)
                import shutil
                shutil.copy2(prev_path, current_path)

                self._json_response({"ok": True})
            except Exception as e:
                self._json_response({"error": str(e)}, 500)

        else:
            self.send_response(404)
            self.end_headers()

    def _json_response(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        # Quiet down static file logging, only show API calls
        if "/api/" in (args[0] if args else ""):
            super().log_message(format, *args)


if __name__ == "__main__":
    PREV_DIR.mkdir(parents=True, exist_ok=True)
    port = 8642
    server = HTTPServer(("", port), CardServer)
    print(f"Card catalog server running at http://localhost:{port}/viewer/")
    print(f"API endpoints: /api/save-card, /api/generate-art, /api/gen-status, /api/previous-art, /api/restore-art")
    server.serve_forever()
