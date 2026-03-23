#!/usr/bin/env bash
# setup.sh — Pre-download the capiscio-core binary for offline use.
#
# Run this BEFORE arriving at PyCon.  Conference wifi is not reliable
# enough for a 15 MB download.
#
# Usage:
#   chmod +x setup.sh && ./setup.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  CapiscIO Demo Setup                                    ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# ── 1. Python venv ───────────────────────────────────────────────────────
if [ ! -d "$SCRIPT_DIR/.venv" ]; then
    echo "→ Creating Python virtual environment..."
    python3 -m venv "$SCRIPT_DIR/.venv"
fi

echo "→ Activating venv and installing dependencies..."
# shellcheck disable=SC1091
source "$SCRIPT_DIR/.venv/bin/activate"
pip install --upgrade pip -q
pip install -r "$SCRIPT_DIR/requirements.txt" -q

# ── 2. Pre-download capiscio-core binary ─────────────────────────────────
echo ""
echo "→ Pre-downloading capiscio-core binary..."
python3 -c "
from capiscio_mcp._core.lifecycle import ensure_binary
path = ensure_binary()
print(f'  Binary cached at: {path}')
"

# ── 3. Verify .env ──────────────────────────────────────────────────────
echo ""
if [ -f "$SCRIPT_DIR/.env" ]; then
    echo "✓ .env file found"
else
    echo "⚠ No .env file found. Copy .env.example to .env and fill in your credentials:"
    echo "    cp .env.example .env"
fi

echo ""
echo "✓ Setup complete. Run the demo with:"
echo "    source .venv/bin/activate"
echo "    python run_demo.py"
