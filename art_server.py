#!/usr/bin/env python3
"""Persistent FLUX model server. Loads model once, generates on demand via HTTP."""

import json
import re
import yaml
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

ART_DIR = Path(__file__).parent / "art"
STYLES_FILE = Path(__file__).parent / "art.yaml"
PREV_DIR = ART_DIR / "previous"

# Generation settings
WIDTH = 768
HEIGHT = 512
STEPS = 4
SEED = 42
QUANTIZE = 4

model = None
model_lock = threading.Lock()


def load_model():
    global model
    print("Loading FLUX2 Klein 4b (quantize=4)... this takes ~15s on first run")
    from mflux.models.flux2.variants.txt2img.flux2_klein import Flux2Klein
    model = Flux2Klein(quantize=QUANTIZE)
    print("Model loaded and ready!")


def load_styles():
    with open(STYLES_FILE) as f:
        styles = yaml.safe_load(f)
    return {s["id"]: s for s in styles}


def generate(prompt, output_path, seed=SEED):
    """Generate an image with the loaded model."""
    with model_lock:
        # Move existing to previous
        if output_path.exists():
            PREV_DIR.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            prev_path = PREV_DIR / f"{output_path.stem}_{ts}{output_path.suffix}"
            output_path.rename(prev_path)

        image = model.generate_image(
            seed=seed,
            prompt=prompt,
            num_inference_steps=STEPS,
            height=HEIGHT,
            width=WIDTH,
        )
        image.image.save(str(output_path))
    return output_path


class ArtHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/generate":
            self.send_error(404)
            return

        content_len = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(content_len))

        art_file = body.get("art_file", "")
        art_prompt = body.get("art_prompt", "")
        art_style = body.get("art_style")
        seed = body.get("seed", SEED)

        if not art_file or not art_prompt:
            self._json({"error": "art_file and art_prompt required"}, 400)
            return

        # Build full prompt with style
        styles = load_styles()
        style_prompt = ""
        if art_style and art_style in styles:
            style_prompt = styles[art_style]["prompt"]
        parts = [p for p in [style_prompt, art_prompt] if p]
        full_prompt = ", ".join(parts)

        output_path = ART_DIR / art_file
        try:
            generate(full_prompt, output_path, seed=seed)
            self._json({"ok": True, "path": str(output_path)})
        except Exception as e:
            self._json({"error": str(e)}, 500)

    def do_GET(self):
        if self.path == "/health":
            self._json({"status": "ready" if model else "loading"})
        else:
            self.send_error(404)

    def _json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        print(f"[art] {args[0]}")


if __name__ == "__main__":
    ART_DIR.mkdir(exist_ok=True)
    PREV_DIR.mkdir(parents=True, exist_ok=True)
    load_model()
    port = 8643
    server = HTTPServer(("127.0.0.1", port), ArtHandler)
    print(f"Art server listening on http://localhost:{port}")
    server.serve_forever()
