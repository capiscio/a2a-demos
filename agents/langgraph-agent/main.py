"""
LangGraph Stateful Agent with CapiscIO Security

This demonstrates a graph-based workflow with:
1. "Let's Encrypt" style one-liner identity setup
2. Automatic badge management via CapiscIO.connect()
3. Real-time event emission showing LangGraph node transitions
"""

import asyncio
import logging
import os
import sys
import uuid
from contextlib import asynccontextmanager
from operator import add
from pathlib import Path
from typing import Annotated, Optional, TypedDict

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

# Add shared module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from capiscio_events import EventEmitter, EventType

# CapiscIO SDK - "Let's Encrypt" style agent identity
try:
    from capiscio_sdk import CapiscIO, SecurityConfig
    from capiscio_sdk.connect import AgentIdentity
    CAPISCIO_SDK_AVAILABLE = True
except ImportError:
    CAPISCIO_SDK_AVAILABLE = False
    CapiscIO = None
    AgentIdentity = None
    SecurityConfig = None

try:
    from capiscio_sdk.integrations.fastapi import CapiscioMiddleware
except ImportError:
    CapiscioMiddleware = None

# LangGraph imports
from langgraph.graph import END, StateGraph

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("langgraph-agent")

# Load environment
load_dotenv()

# Configuration
AGENT_NAME = "LangGraph Support Agent"
CAPISCIO_SERVER = os.environ.get("CAPISCIO_SERVER_URL", "https://registry.capisc.io")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
PORT = int(os.environ.get("LANGGRAPH_AGENT_PORT", "8003"))
SECURITY_MODE = os.environ.get("SECURITY_MODE", "ca")  # 'dev' or 'ca'

# Global instances
events: Optional[EventEmitter] = None
agent: Optional["AgentIdentity"] = None
security_config: Optional["SecurityConfig"] = None

# A2A Agent Card (static parts - stored in registry and served at /.well-known/agent.json)
AGENT_CARD = {
    "name": AGENT_NAME,
    "description": "Customer support agent with intelligent routing workflow",
    "url": f"http://localhost:{PORT}",
    "version": "1.0.0",
    "capabilities": {
        "streaming": False,
        "pushNotifications": False,
    },
    "skills": [
        {
            "id": "support",
            "name": "Customer Support",
            "description": "Route and handle customer support requests",
        }
    ],
    "authentication": {"schemes": ["capiscio-badge"]},
}


# ==============================================================================
# State Definition
# ==============================================================================

class SupportState(TypedDict):
    """State for the customer support workflow."""
    # User's original message
    user_message: str
    # Classification of the request
    category: str
    # Accumulated context from handlers
    context: Annotated[list[str], add]
    # Final response
    response: str
    # Conversation history
    messages: list[dict]


# ==============================================================================
# Graph Nodes
# ==============================================================================

def emit_node_start(node_name: str, state: dict):
    """Emit node start event."""
    if events:
        events.emit(
            EventType.LANGGRAPH_NODE_START,
            {"node": node_name, "state_keys": list(state.keys())},
        )


def emit_node_end(node_name: str, updates: dict):
    """Emit node end event."""
    if events:
        events.emit(
            EventType.LANGGRAPH_NODE_END,
            {"node": node_name, "updates": list(updates.keys())},
        )


def emit_edge(from_node: str, to_node: str, condition: str = ""):
    """Emit edge taken event."""
    if events:
        events.emit(
            EventType.LANGGRAPH_EDGE_TAKEN,
            {"from": from_node, "to": to_node, "condition": condition},
        )


def classify_request(state: SupportState) -> dict:
    """Classify the user's request into a category."""
    emit_node_start("classify_request", state)

    message = state["user_message"].lower()

    # Simple keyword-based classification
    if any(word in message for word in ["bug", "error", "crash", "not working", "broken", "technical"]):
        category = "technical"
    elif any(word in message for word in ["bill", "charge", "payment", "invoice", "refund", "subscription"]):
        category = "billing"
    else:
        category = "general"

    updates = {
        "category": category,
        "context": [f"Request classified as: {category}"],
    }

    emit_node_end("classify_request", updates)

    if events:
        events.emit(
            EventType.LANGGRAPH_STATE_UPDATE,
            {"category": category},
        )

    return updates


def route_to_handler(state: SupportState) -> str:
    """Route to the appropriate support handler."""
    category = state.get("category", "general")

    routes = {
        "technical": "tech_support",
        "billing": "billing_support",
        "general": "general_support",
    }

    destination = routes.get(category, "general_support")
    emit_edge("route_to_handler", destination, f"category={category}")

    return destination


def tech_support(state: SupportState) -> dict:
    """Handle technical support requests."""
    emit_node_start("tech_support", state)

    context_update = [
        "Technical support team engaged",
        "Checking for known issues...",
        "Preparing troubleshooting steps",
    ]

    updates = {"context": context_update}
    emit_node_end("tech_support", updates)

    return updates


def billing_support(state: SupportState) -> dict:
    """Handle billing support requests."""
    emit_node_start("billing_support", state)

    context_update = [
        "Billing team engaged",
        "Reviewing account status...",
        "Preparing billing information",
    ]

    updates = {"context": context_update}
    emit_node_end("billing_support", updates)

    return updates


def general_support(state: SupportState) -> dict:
    """Handle general support requests."""
    emit_node_start("general_support", state)

    context_update = [
        "General support team engaged",
        "Gathering relevant information...",
    ]

    updates = {"context": context_update}
    emit_node_end("general_support", updates)

    return updates


def generate_response(state: SupportState) -> dict:
    """Generate the final response using accumulated context."""
    emit_node_start("generate_response", state)

    category = state.get("category", "general")
    context = state.get("context", [])
    user_message = state.get("user_message", "")

    # Build response based on category and context
    category_intros = {
        "technical": "I understand you're experiencing a technical issue.",
        "billing": "I can help you with your billing inquiry.",
        "general": "Thank you for reaching out.",
    }

    intro = category_intros.get(category, "Thank you for your message.")

    response = f"""{intro}

Based on your message: "{user_message[:100]}..."

Processing steps completed:
{chr(10).join(f"  • {c}" for c in context)}

Our team is ready to assist you further. Is there anything specific you'd like help with?"""

    updates = {"response": response}
    emit_node_end("generate_response", updates)

    return updates


# ==============================================================================
# Graph Construction
# ==============================================================================

def create_support_graph() -> StateGraph:
    """Create the customer support workflow graph."""

    # Create graph with state schema
    workflow = StateGraph(SupportState)

    # Add nodes
    workflow.add_node("classify_request", classify_request)
    workflow.add_node("tech_support", tech_support)
    workflow.add_node("billing_support", billing_support)
    workflow.add_node("general_support", general_support)
    workflow.add_node("generate_response", generate_response)

    # Set entry point
    workflow.set_entry_point("classify_request")

    # Add conditional routing
    workflow.add_conditional_edges(
        "classify_request",
        route_to_handler,
        {
            "tech_support": "tech_support",
            "billing_support": "billing_support",
            "general_support": "general_support",
        }
    )

    # All handlers flow to response generation
    workflow.add_edge("tech_support", "generate_response")
    workflow.add_edge("billing_support", "generate_response")
    workflow.add_edge("general_support", "generate_response")

    # End after response
    workflow.add_edge("generate_response", END)

    return workflow.compile()


def run_workflow_with_events(user_message: str) -> str:
    """Run the support workflow and emit events."""
    _trace_id = events.new_trace()  # Sets up tracing context
    task_id = str(uuid.uuid4())[:8]

    events.task_started(task_id, "support_workflow", {"message": user_message[:100]})

    try:
        # Create and run graph
        graph = create_support_graph()

        initial_state: SupportState = {
            "user_message": user_message,
            "category": "",
            "context": [],
            "response": "",
            "messages": [],
        }

        # Run the graph
        result = graph.invoke(initial_state)

        response = result.get("response", "Unable to generate response")

        events.task_completed(task_id, {
            "category": result.get("category"),
            "context_count": len(result.get("context", [])),
        })

        return response

    except Exception as e:
        events.task_failed(task_id, str(e))
        raise


# ==============================================================================
# FastAPI Application
# ==============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    global events, agent, security_config

    # Load security configuration from environment
    if SecurityConfig:
        security_config = SecurityConfig.from_env()
        logger.info(f"🔒 Security config: require_signatures={security_config.downstream.require_signatures}, fail_mode={security_config.fail_mode}")

    # CapiscIO.connect() - "Let's Encrypt" style one-liner setup
    # Handles: key generation, DID derivation, registration, badge request
    if CAPISCIO_SDK_AVAILABLE:
        try:
            agent = CapiscIO.connect(
                api_key=os.environ.get("CAPISCIO_API_KEY", ""),
                name=AGENT_NAME,
                server_url=CAPISCIO_SERVER,
                dev_mode=(SECURITY_MODE == "dev"),
                keys_dir=Path(os.path.dirname(os.path.abspath(__file__))) / ".capiscio" / "keys",
                agent_card=AGENT_CARD,
            )
            logger.info(f"🔑 Agent DID: {agent.did}")
            logger.info(f"🔐 Badge: {'acquired' if agent.badge else 'pending'}")
        except Exception as e:
            logger.warning(f"⚠️  CapiscIO identity setup failed: {e}")
            agent = None

    # Initialize event emitter for framework-specific events
    events = EventEmitter(
        server_url=agent.server_url if agent else CAPISCIO_SERVER,
        api_key=agent.api_key if agent else os.environ.get("CAPISCIO_API_KEY", ""),
        agent_id=agent.agent_id if agent else "",
        agent_name=AGENT_NAME,
    )

    events.agent_started({
        "framework": "langgraph",
        "mode": SECURITY_MODE,
        "workflow": "customer_support",
        "port": PORT,
        "did": agent.did if agent else None,
    })

    logger.info(f"🚀 {AGENT_NAME} started on port {PORT}")
    logger.info(f"📊 Events visible at {CAPISCIO_SERVER.replace(':8080', ':3000')}/events")

    yield

    if agent:
        agent.close()
    events.agent_stopped()
    events.close()


app = FastAPI(
    title=AGENT_NAME,
    description="A2A-compliant stateful agent built with LangGraph",
    lifespan=lifespan,
)
# Note: Middleware requires guard which is only available after connect().
# Badge enforcement is handled in the /tasks/send endpoint via verify_badge_with_sdk().


@app.get("/.well-known/agent.json")
async def get_agent_card():
    """Serve A2A Agent Card."""
    agent_did = agent.did if agent else "did:web:localhost:agents:langgraph"

    return {
        **AGENT_CARD,
        "x-capiscio": {
            "did": agent_did,
            "trustLevel": "0" if SECURITY_MODE == "dev" else "1",
            "badgeEndpoint": f"{CAPISCIO_SERVER}/v1/validate",
        }
    }


# SDK-based badge verification using SimpleGuard
# Replaces manual HTTP calls - leverages the SDK's built-in verification
async def verify_badge_with_sdk(badge_token: Optional[str], body: bytes = b"") -> dict:
    """
    Verify a CapiscIO badge using the SDK's SimpleGuard.
    This is the proper way - use SDK functionality, not custom HTTP calls!

    Returns: {"valid": bool, "agent_id": str, "trust_level": int, "error": str}
    """
    if not badge_token:
        return {"valid": False, "error": "No badge provided"}

    if not agent or not hasattr(agent, '_guard'):
        return {"valid": False, "error": "SimpleGuard not available"}

    try:
        # Use SDK's verify_inbound - handles JWS verification, expiry, etc.
        payload = agent._guard.verify_inbound(badge_token, body=body)
        return {
            "valid": True,
            "agent_id": payload.get("iss", "unknown"),
            "trust_level": payload.get("trust_level", payload.get("vc", {}).get("level", 0)),
            "payload": payload,
        }
    except Exception as e:
        return {"valid": False, "error": str(e)}


@app.post("/tasks/send")
async def send_task(request: Request, x_capiscio_badge: Optional[str] = Header(None)):
    """
    Handle incoming A2A task with SDK-based badge enforcement.

    Security controlled via environment:
    - CAPISCIO_REQUIRE_SIGNATURES=true  -> Require valid badges
    - CAPISCIO_FAIL_MODE=block          -> Return 403 on failure (vs log/monitor)
    - CAPISCIO_MIN_TRUST_LEVEL=1        -> Minimum trust level required
    """
    body = await request.body()
    body_json = await request.json()
    task_id = body_json.get("id", str(uuid.uuid4()))

    # Use SDK's SecurityConfig (loaded from env vars)
    require_badge = security_config.downstream.require_signatures if security_config else False
    fail_mode = security_config.fail_mode if security_config else "log"
    min_trust = int(os.getenv("CAPISCIO_MIN_TRUST_LEVEL", "0"))

    # Verify badge using SDK's SimpleGuard
    badge_info = await verify_badge_with_sdk(x_capiscio_badge, body)

    events.emit(
        EventType.A2A_REQUEST_RECEIVED,
        {
            "task_id": task_id,
            "authenticated": badge_info.get("valid", False),
            "caller_agent": badge_info.get("agent_id"),
            "trust_level": badge_info.get("trust_level"),
            "enforcement": {"require": require_badge, "mode": fail_mode},
        },
    )

    # BLOCK if badge required but not valid
    if require_badge and not badge_info.get("valid"):
        logger.warning(f"BLOCKED task {task_id}: {badge_info.get('error')}")
        events.emit(
            EventType.A2A_REQUEST_RECEIVED,
            {"task_id": task_id, "blocked": True, "reason": "no_badge", "detail": badge_info.get("error")},
        )
        if fail_mode == "block":
            return JSONResponse(
                status_code=401 if "No badge" in badge_info.get("error", "") else 403,
                content={
                    "id": task_id,
                    "status": {"state": "blocked", "message": f"Badge required: {badge_info.get('error')}"}
                }
            )
        # Monitor/log mode - continue but log warning
        logger.warning(f"[MONITOR] Would block task {task_id} but fail_mode={fail_mode}")

    # BLOCK if trust level too low
    caller_trust = badge_info.get("trust_level", 0)
    if require_badge and caller_trust < min_trust:
        logger.warning(f"BLOCKED task {task_id}: trust level {caller_trust} < {min_trust}")
        events.emit(
            EventType.A2A_REQUEST_RECEIVED,
            {"task_id": task_id, "blocked": True, "reason": "low_trust", "caller_trust": caller_trust, "required": min_trust},
        )
        if fail_mode == "block":
            return JSONResponse(
                status_code=403,
                content={
                    "id": task_id,
                    "status": {"state": "blocked", "message": f"Trust level {caller_trust} below required {min_trust}"}
                }
            )

    # Extract message
    message = body_json.get("message", {})
    parts = message.get("parts", [])
    user_message = ""
    for part in parts:
        if part.get("type") == "text":
            user_message += part.get("text", "")

    if not user_message:
        raise HTTPException(status_code=400, detail="No message provided")

    try:
        result = await asyncio.to_thread(run_workflow_with_events, user_message)

        return {
            "id": task_id,
            "status": {"state": "completed"},
            "artifacts": [
                {"parts": [{"type": "text", "text": result}]}
            ]
        }

    except Exception as e:
        logger.exception("Workflow failed")
        return JSONResponse(
            status_code=500,
            content={
                "id": task_id,
                "status": {"state": "failed", "message": str(e)}
            }
        )


@app.get("/health")
async def health():
    return {"status": "healthy", "agent": AGENT_NAME}


# ==============================================================================
# Interactive Demo Mode
# ==============================================================================

async def demo_mode():
    """Run interactive demo."""
    print("\n" + "="*60)
    print(f"🤖 {AGENT_NAME} - Interactive Demo Mode")
    print("="*60)
    print("\n📊 Events visible at: https://app.capisc.io/events")
    print("\nExample queries:")
    print("  • 'My app keeps crashing when I click save'")
    print("  • 'I was charged twice for my subscription'")
    print("  • 'How do I reset my password?'")
    print("\nType 'quit' to exit\n")

    while True:
        try:
            message = input("\n💬 Enter your support request: ").strip()
            if message.lower() in ["quit", "exit", "q"]:
                break
            if not message:
                continue

            print("\n🔄 Processing through support workflow...")
            print("Watch the dashboard to see node transitions!\n")

            result = run_workflow_with_events(message)

            print("\n" + "="*60)
            print("📋 RESPONSE")
            print("="*60)
            print(result)

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")


# ==============================================================================
# Main Entry Point
# ==============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=AGENT_NAME)
    parser.add_argument("--serve", action="store_true", help="Run as HTTP server")
    parser.add_argument("--port", type=int, default=PORT, help="Server port")
    args = parser.parse_args()

    if args.serve:
        uvicorn.run(app, host="0.0.0.0", port=args.port)
    else:
        # Initialize agent via CapiscIO.connect() - one-liner setup
        if CAPISCIO_SDK_AVAILABLE:
            try:
                agent = CapiscIO.connect(
                    api_key=os.environ.get("CAPISCIO_API_KEY", ""),
                    name=AGENT_NAME,
                    server_url=CAPISCIO_SERVER,
                    dev_mode=True,
                    keys_dir=Path(os.path.dirname(os.path.abspath(__file__))) / ".capiscio" / "keys",
                    agent_card=AGENT_CARD,
                )
                logger.info(f"🔑 Agent DID: {agent.did}")
            except Exception as e:
                logger.warning(f"⚠️  CapiscIO identity not available: {e}")

        events = EventEmitter(
            server_url=agent.server_url if agent else CAPISCIO_SERVER,
            api_key=agent.api_key if agent else os.environ.get("CAPISCIO_API_KEY", ""),
            agent_id=agent.agent_id if agent else "",
            agent_name=AGENT_NAME,
        )
        events.agent_started({"mode": "interactive", "framework": "langgraph", "did": agent.did if agent else None})

        try:
            asyncio.run(demo_mode())
        finally:
            if agent:
                agent.close()
            events.agent_stopped()
            events.close()
