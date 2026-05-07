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

# ── Scaffold .env ────────────────────────────────────────
echo ""
if [ -f ".env" ]; then
    echo "✓  .env file found"
else
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
    echo "⚠️  Created .env from .env.example — edit it with your credentials:"
    echo "    $(pwd)/.env"
    echo ""
    echo "   Required:"
    echo "     CAPISCIO_API_KEY   — from https://app.capisc.io → Settings → API Keys"
    echo "     CAPISCIO_SERVER_ID — from https://app.capisc.io → MCP Servers (or set to 'auto')"
fi

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  Setup complete!"
echo ""
echo "  Next steps:"
echo "    1. Edit .env with your credentials (if just created)"
echo "    2. python scripts/setup_policies.py  (create policies)"
echo "    3. source .venv/bin/activate"
echo "    4. python run_demo.py"
echo "═══════════════════════════════════════════════════════"
