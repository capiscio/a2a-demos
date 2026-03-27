"""
Demo Two — Guarded MCP Server.

Same MCP server as demo-one with three tools at different trust levels:

  Tool              Min Trust Level   Who can call it
  ──────────────────────────────────────────────────────
  get_price          0 (open)         Any agent
  place_order        2 (DV+)          Domain-validated agents
  cancel_all_orders  4 (EV)           Extended-validation agents

What's different in demo-two: the ORG POLICY can override these levels
at runtime.  The @guard decorator queries the embedded PDP, which
evaluates the active policy bundle.  When the admin changes the policy
in the dashboard, enforcement changes — no code deploy needed.

Run:
    python server/main.py

Requires:
    CAPISCIO_SERVER_ID   — MCP server UUID (from dashboard)
    CAPISCIO_API_KEY     — Registry API key
    CAPISCIO_SERVER_URL  — Registry URL (default: https://registry.capisc.io)
"""

import asyncio
import logging
import os
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("demo-two.server")

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from capiscio_mcp import MCPServerIdentity  # noqa: E402
from capiscio_mcp.integrations.mcp import CapiscioMCPServer  # noqa: E402


# ── Simulated data ───────────────────────────────────────────────────────
CATALOG = {
    "WIDGET-A": {"name": "Widget Alpha", "price": 9.99},
    "WIDGET-B": {"name": "Widget Beta", "price": 24.50},
    "WIDGET-C": {"name": "Widget Gamma", "price": 149.00},
}

ORDERS: list[dict] = []


async def build_server() -> CapiscioMCPServer:
    """Connect to CapiscIO and register guarded MCP tools."""

    identity = await MCPServerIdentity.from_env()
    logger.info("Server DID  : %s", identity.did)
    logger.info("Badge ready : %s", "yes" if identity.badge else "no")

    server = CapiscioMCPServer(identity=identity)

    # ── Trust Level 0: open to any caller ─────────────────────────────
    @server.tool(min_trust_level=0)
    async def get_price(sku: str) -> str:
        """Look up the price of a product by SKU."""
        item = CATALOG.get(sku.upper())
        if not item:
            return f"Unknown SKU: {sku}"
        return f"{item['name']}: ${item['price']:.2f}"

    # ── Trust Level 2: requires domain-validated (DV) badge ───────────
    @server.tool(min_trust_level=2)
    async def place_order(sku: str, quantity: int) -> str:
        """Place an order for a product. Requires DV+ trust level."""
        item = CATALOG.get(sku.upper())
        if not item:
            return f"Unknown SKU: {sku}"
        if quantity < 1:
            return "Quantity must be at least 1"
        order = {
            "id": len(ORDERS) + 1,
            "sku": sku.upper(),
            "name": item["name"],
            "quantity": quantity,
            "total": item["price"] * quantity,
        }
        ORDERS.append(order)
        return f"Order #{order['id']} placed: {quantity}x {item['name']} = ${order['total']:.2f}"

    # ── Trust Level 4: requires extended-validation (EV) badge ────────
    @server.tool(min_trust_level=4)
    async def cancel_all_orders() -> str:
        """Cancel all pending orders. Requires EV trust level."""
        count = len(ORDERS)
        ORDERS.clear()
        return f"Cancelled {count} order(s)"

    return server


def main() -> None:
    server = asyncio.run(build_server())
    logger.info("Starting MCP server (stdio)…")
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
