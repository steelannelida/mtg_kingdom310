#!/usr/bin/env python3
"""Batch generate art for all cards missing images, one at a time via the art server."""

import json
import re
import subprocess
import sys
import time
import yaml
from pathlib import Path

ROOT = Path(__file__).parent
CARDS_DIR = ROOT / "cards"
ART_DIR = ROOT / "art"
ART_SERVER = "http://127.0.0.1:8643"


def curl_get(url, timeout=15):
    result = subprocess.run(
        ["curl", "-s", "--max-time", str(timeout), url],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"curl failed: {result.stderr}")
    return json.loads(result.stdout)


def curl_post(url, data, timeout=600):
    result = subprocess.run(
        ["curl", "-s", "--max-time", str(timeout),
         "-H", "Content-Type: application/json",
         "-d", json.dumps(data), url],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"curl failed: {result.stderr}")
    return json.loads(result.stdout)


def check_server():
    try:
        data = curl_get(f"{ART_SERVER}/health", timeout=15)
        return data.get("status") == "ready"
    except Exception as e:
        print(f"Art server not reachable: {e}")
        return False


def generate_card(card):
    art_file = card.get("art_file", "")
    if not art_file:
        name = card["name"].lower()
        art_file = re.sub(r'[^a-z0-9]+', '_', name).strip('_') + ".png"

    return curl_post(f"{ART_SERVER}/generate", {
        "art_file": art_file,
        "art_prompt": card.get("art_prompt", ""),
        "art_style": card.get("art_style"),
        "seed": 42,
    }, timeout=600)


def main():
    if not check_server():
        print("ERROR: Art server is not running. Start it with: python art_server.py")
        sys.exit(1)

    print("Art server ready.\n")

    with open(CARDS_DIR / "manifest.yaml") as f:
        manifest = yaml.safe_load(f)

    to_generate = []
    for rel_path in manifest["files"]:
        yaml_path = CARDS_DIR / rel_path
        with open(yaml_path) as f:
            cards = yaml.safe_load(f) or []
        for card in cards:
            art_file = card.get("art_file", "")
            if not art_file:
                name = card["name"].lower()
                art_file = re.sub(r'[^a-z0-9]+', '_', name).strip('_') + ".png"
            if not (ART_DIR / art_file).exists() and card.get("art_prompt"):
                to_generate.append((rel_path, card))
            # Also check back face
            bf = card.get("back_face")
            if bf and bf.get("art_file") and not (ART_DIR / bf["art_file"]).exists() and bf.get("art_prompt"):
                to_generate.append((rel_path, bf))

    total = len(to_generate)
    print(f"Found {total} cards to generate.\n")

    done = 0
    errors = 0
    for i, (source, card) in enumerate(to_generate, 1):
        name = card["name"]
        print(f"[{i}/{total}] {name}", flush=True)
        t0 = time.time()
        try:
            result = generate_card(card)
            elapsed = time.time() - t0
            if result.get("ok"):
                done += 1
                print(f"  done in {elapsed:.0f}s", flush=True)
            else:
                errors += 1
                print(f"  ERROR: {result.get('error', 'unknown')}", flush=True)
        except Exception as e:
            errors += 1
            print(f"  EXCEPTION: {e}", flush=True)

    print(f"\nBatch complete: {done} generated, {errors} errors.")


if __name__ == "__main__":
    main()
