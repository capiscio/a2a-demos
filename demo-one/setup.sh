#!/usr/bin/env bash
# setup.sh — Setup Demo One environment.
#
# Usage:
#   ./setup.sh           # Install from PyPI
#   ./setup.sh --local   # Install from local repos (pre-release testing)
#
# Run this BEFORE arriving at PyCon.  Conference wifi is not reliable
# enough for a 15 MB download.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Parse flags
USE_LOCAL=false
for arg in "$@"; do
    case $arg in
        --local) USE_LOCAL=true ;;
    esac
done

echo "╔══════════════════════════════════════════════════════════╗"
if [ "$USE_LOCAL" = true ]; then
echo "║  CapiscIO Demo One Setup — LOCAL REPOS                  ║"
else
echo "║  CapiscIO Demo One Setup — PyPI                         ║"
fi
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

if [ "$USE_LOCAL" = true ]; then
    # Install local CapiscIO packages first
    pip install -e "$SCRIPT_DIR/../../capiscio-sdk-python" -q
    pip install -e "$SCRIPT_DIR/../../capiscio-mcp-python[mcp]" -q
    # Then install remaining deps (dotenv, httpx, etc.)
    pip install python-dotenv httpx -q
    echo "  ✓ Using local repos (editable installs)"
else
    pip install -r "$SCRIPT_DIR/requirements.txt" -q
fi

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
