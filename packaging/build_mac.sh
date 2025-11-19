#!/usr/bin/env bash
set -euo pipefail

# Build macOS .app for LitRelevanceAI (PyQt6 GUI)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

python3 -m pip install --upgrade pip pyinstaller

pyinstaller "$SCRIPT_DIR/pyinstaller/litrx.spec"

echo
echo "Build succeeded. App is under dist/LitRelevanceAI.app"
echo "Distribute the .app or wrap with a DMG as needed."

