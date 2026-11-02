#!/bin/bash
# Copy TNK custom files into Forge.
set -e
CUSTOM="/Users/dmitrychernenkov/Library/Application Support/Forge/custom"
mkdir -p "$CUSTOM/cards" "$CUSTOM/editions" "$CUSTOM/tokens"
cp cards/*.txt  "$CUSTOM/cards/"
cp editions/*.txt "$CUSTOM/editions/"
cp tokens/*.txt "$CUSTOM/tokens/"
echo "Installed. Restart Forge to load the set."
