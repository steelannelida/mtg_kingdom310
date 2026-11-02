#!/usr/bin/env python3
"""Regenerate only the cards listed in notes.md 'To regenerate' section."""

import yaml, glob
from generate_art import load_styles, generate_card_art, ART_DIR

REGEN_SUBSTRINGS = [
    'Vityaz Storozhevoy', 'Pakhar', 'Derevenskaya Devitsa', 'Svetly Otrok',
    'Monastery', 'Blagoslovenie', 'Den Prostoyat',
    'Kupets na Pristani', 'Chudo-Rybka', 'Morskoy Kon',
    'Bluddyechko', 'Veschiy Son', 'V Bochke',
    'Chert Melkiy', 'Kladbishchenskiy', 'Sglaz', 'Noch Proderzhatsa',
    'Udaloy Molodets', 'Okhrabrevshiy', 'Samokhodnaya Pech',
    'Kyyryy Oyuun', 'Udal Molodetskaya', 'Grom i Molniya',
    'shuchyemu', 'Klich Bogatyrskiy', 'Tantsy', 'Ne Skhodi',
    'Ukrast Tsarevnu',
    'Priyut Leshego', 'Lapot Samokhodny', 'Klubochek',
    'Gorshochek Kashi', 'Dubinka',
]

def should_regen(card_name):
    for r in REGEN_SUBSTRINGS:
        if r.lower() in card_name.lower():
            return True
    return False

ART_DIR.mkdir(exist_ok=True)
styles = load_styles()
count = 0

for f in sorted(glob.glob('cards/common/*.yaml')):
    with open(f) as fh:
        cards = yaml.safe_load(fh)
    for card in cards:
        if should_regen(card['name']) and card.get('art_file'):
            print(f"\n[{card['name']}]")
            generate_card_art(card, styles, seed=42, force=True)
            count += 1

print(f"\nDone! Regenerated {count} cards.")
