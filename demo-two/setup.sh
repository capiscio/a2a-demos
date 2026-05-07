#!/usr/bin/env bash
# Demo Two — Setup Script
#
# Usage:
#   ./setup.sh           # Install from PyPI
#   ./setup.sh --local   # Install from local repos (pre-release testing)
#
# Run this BEFORE the demo (e.g., at home before PyCon) so
# everything works offline / on slow conference Wi-Fi.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Parse flags
USE_LOCAL=false
for arg in "$@"; do
    case $arg in
        --local) USE_LOCAL=true ;;
    esac
done

echo "═══════════════════════════════════════════════════════"
if [ "$USE_LOCAL" = true ]; then
echo "  CapiscIO Demo Two — Setup (LOCAL REPOS)"
else
echo "  CapiscIO Demo Two — Setup (PyPI)"
fi
echo "═══════════════════════════════════════════════════════"

# ── Virtual environment ──────────────────────────────────
if [ ! -d ".venv" ]; then
    echo ""
    echo "Creating virtual environment…"
    python3 -m venv .venv
fi

echo ""
echo "Activating virtual environment…"
source .venv/bin/activate

# ── Dependencies ─────────────────────────────────────────
echo ""
echo "Installing dependencies…"
pip install -q --upgrade pip

if [ "$USE_LOCAL" = true ]; then
    pip install -q -e "$SCRIPT_DIR/../../capiscio-sdk-python"
    pip install -q -e "$SCRIPT_DIR/../../capiscio-mcp-python[mcp]"
    pip install -q python-dotenv httpx pyyaml
    echo "  ✓ Using local repos (editable installs)"
else
    pip install -q -r requirements.txt
fi

# ── Pre-download capiscio-core binary ────────────────────
echo ""
echo "Pre-downloading capiscio-core binary…"
python3 -c "from capiscio_mcp._core.lifecycle import ensure_binary; ensure_binary()"

# ── .env check ───────────────────────────────────────────
echo ""
if [ ! -f ".env" ]; then
    echo "⚠  No .env file found."
    echo "   Copy .env.example to .env and fill in your values:"
    echo "   cp .env.example .env"
else
    echo "✓  .env file found"
fi

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  Setup complete!"
echo ""
echo "  Next steps:"
echo "    1. cp .env.example .env  (if not done)"
echo "    2. Fill in credentials in .env"
echo "    3. python scripts/setup_policies.py  (create policies)"
echo "    4. source .venv/bin/activate"
echo "    5. python run_demo.py"
echo "═══════════════════════════════════════════════════════"
