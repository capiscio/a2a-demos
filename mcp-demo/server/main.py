"""
CapiscIO MCP Demo Server — Guarded filesystem tools.

Demonstrates "Let's Encrypt" style MCP server identity:
  1. Calls MCPServerIdentity.connect() once at startup
  2. Registers DID + public key with the CapiscIO registry
  3. Issues a trust badge and starts auto-renewal
  4. Injects server identity (_meta) into every MCP initialize response
  5. Enforces per-tool trust-level requirements via @server.tool(min_trust_level=N)

Run:
    python server/main.py

Environment variables (see .env.example):
    CAPISCIO_SERVER_ID   — UUID of this MCP server (from the dashboard)
    CAPISCIO_API_KEY     — Registry API key (sk_live_... or sk_test_...)
    CAPISCIO_SERVER_URL  — Registry URL (default: https://registry.capisc.io)
"""

import asyncio
import logging
import os
import sys

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CapiscIO imports
# ---------------------------------------------------------------------------
from capiscio_mcp import MCPServerIdentity  # noqa: E402
from capiscio_mcp.integrations.mcp import CapiscioMCPServer  # noqa: E402


async def build_server() -> CapiscioMCPServer:
    """Connect to CapiscIO and wire up the MCP server."""

    # ── One-liner identity setup ──────────────────────────────────────────
    # Reads CAPISCIO_SERVER_ID, CAPISCIO_API_KEY, CAPISCIO_SERVER_URL
    identity = await MCPServerIdentity.from_env()
    logger.info("Server DID  : %s", identity.did)
    logger.info("Badge ready : %s", "yes" if identity.badge else "no")

    # ── Create guarded MCP server ─────────────────────────────────────────
    server = CapiscioMCPServer(identity=identity)

    # ── Tool definitions ──────────────────────────────────────────────────

    # Restrict filesystem tools to a safe demo directory
    ALLOWED_ROOT = os.environ.get("DEMO_ALLOWED_ROOT", "/tmp/capiscio-demo")
    os.makedirs(ALLOWED_ROOT, exist_ok=True)

    def _safe_path(user_path: str) -> str:
        """Resolve user_path and ensure it's within ALLOWED_ROOT."""
        resolved = os.path.realpath(os.path.join(ALLOWED_ROOT, user_path))
        if not resolved.startswith(os.path.realpath(ALLOWED_ROOT)):
            raise ValueError(f"Path traversal denied: {user_path!r} resolves outside allowed root")
        return resolved

    @server.tool(min_trust_level=0)
    async def list_files(directory: str) -> list:
        """List files in a directory (open to any caller, trust level 0)."""
        try:
            safe_dir = _safe_path(directory)
            return sorted(os.listdir(safe_dir))
        except ValueError as e:
            return [f"Error: {e}"]
        except FileNotFoundError:
            return [f"Error: directory '{directory}' not found"]
        except PermissionError:
            return [f"Error: permission denied for '{directory}'"]

    @server.tool(min_trust_level=2)
    async def read_file(path: str) -> str:
        """Read a file's contents (requires trust level 2+)."""
        safe = _safe_path(path)
        with open(safe) as fh:
            return fh.read()

    @server.tool(min_trust_level=3)
    async def write_file(path: str, content: str) -> str:
        """Write content to a file (requires trust level 3+)."""
        safe = _safe_path(path)
        with open(safe, "w") as fh:
            fh.write(content)
        return f"Written {len(content)} bytes to {path}"

    return server


def main() -> None:
    """Entry point."""
    server = asyncio.run(build_server())
    logger.info("Starting MCP server over stdio transport…")
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
