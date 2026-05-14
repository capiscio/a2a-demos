"""
Enforcement Demo — Guarded MCP Server.

An MCP server with three tools at different access levels:

  Tool              Requirement       Who can call it
  ──────────────────────────────────────────────────────
  get_price          open              Any agent
  place_order        badge required    Agents with CA-issued badge
  cancel_all_orders  badge required    Agents with CA-issued badge

The server obtains its own identity (DID + badge) from the CapiscIO
registry at startup via CapiscioMCPServer.connect().

Run:
    python server/main.py

Requires:
    CAPISCIO_SERVER_ID   — MCP server UUID (from dashboard)
    CAPISCIO_API_KEY     — Registry API key
    CAPISCIO_SERVER_URL  — Registry URL (default: https://registry.capisc.io)
"""

import logging
import os
import sys

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    stream=sys.stderr,
)

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from capiscio_mcp.integrations.mcp import CapiscioMCPServer  # noqa: E402


# ── Simulated data ───────────────────────────────────────────────────────
CATALOG = {
    "WIDGET-A": {"name": "Widget Alpha", "price": 9.99},
    "WIDGET-B": {"name": "Widget Beta", "price": 24.50},
    "WIDGET-C": {"name": "Widget Gamma", "price": 149.00},
}

ORDERS: list[dict] = []


# ── CapiscIO setup (1 line) ──────────────────────────────────────────────
server = CapiscioMCPServer.connect()


# ── Open: no badge required ───────────────────────────────────────────
@server.tool(min_trust_level=0)
async def get_price(sku: str) -> str:
    """Look up the price of a product by SKU."""
    item = CATALOG.get(sku.upper())
    if not item:
        return f"Unknown SKU: {sku}"
    return f"{item['name']}: ${item['price']:.2f}"


# ── Badge required: agents must present a CA-issued badge ─────────────
@server.tool(min_trust_level=1)
async def place_order(sku: str, quantity: int) -> str:
    """Place an order for a product. Requires a valid badge."""
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


# ── Badge required: higher-risk operation ─────────────────────────────
@server.tool(min_trust_level=2)
async def cancel_all_orders() -> str:
    """Cancel all pending orders. Requires a valid badge."""
    count = len(ORDERS)
    ORDERS.clear()
    return f"Cancelled {count} order(s)"


if __name__ == "__main__":
    server.run()
