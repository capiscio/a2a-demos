"""
LangChain Research Agent with CapiscIO Security

This agent demonstrates:
1. A2A-compliant Agent Card serving
2. langchain-capiscio for 3-line trust enforcement
3. Real-time event emission to CapiscIO dashboard
4. Tool-calling agent for research tasks
"""

import asyncio
import logging
import os
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

# Add shared module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from capiscio_events import EventEmitter, EventType

# --------------------------------------------------------------------------
# langchain-capiscio: 3 lines to secure a LangChain agent
# --------------------------------------------------------------------------
try:
    from langchain_capiscio import CapiscioCallbackHandler, CapiscioGuard
    from capiscio_sdk import SecurityConfig
    CAPISCIO_AVAILABLE = True
except ImportError:
    CAPISCIO_AVAILABLE = False
    CapiscioGuard = None
    CapiscioCallbackHandler = None
    SecurityConfig = None

try:
    from capiscio_sdk.integrations.fastapi import CapiscioMiddleware
except ImportError:
    CapiscioMiddleware = None

# LangChain imports
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("langchain-agent")

# Load environment
load_dotenv()

# Configuration
AGENT_NAME = "LangChain Research Agent"
CAPISCIO_SERVER = os.environ.get("CAPISCIO_SERVER_URL", "https://registry.capisc.io")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
PORT = int(os.environ.get("LANGCHAIN_AGENT_PORT", "8001"))
SECURITY_MODE = os.environ.get("SECURITY_MODE", "ca")
KEYS_DIR = Path(os.path.dirname(os.path.abspath(__file__))) / ".capiscio" / "keys"

# A2A Agent Card
AGENT_CARD = {
    "name": AGENT_NAME,
    "description": "A research assistant that can search the web, check time, and calculate.",
    "url": f"http://localhost:{PORT}",
    "version": "1.0.0",
    "capabilities": {
        "streaming": False,
        "pushNotifications": False,
    },
    "skills": [
        {
            "id": "research",
            "name": "Web Research",
            "description": "Search the web and compile research on a topic",
        },
        {
            "id": "calculate",
            "name": "Calculator",
            "description": "Perform mathematical calculations",
        }
    ],
    "authentication": {"schemes": ["capiscio-badge"]},
}

# --------------------------------------------------------------------------
# LINE 1: Create the guard — reads CAPISCIO_API_KEY + config from env
# --------------------------------------------------------------------------
guard: Optional["CapiscioGuard"] = (
    CapiscioGuard(
        mode="log",
        connect_kwargs={
            "name": AGENT_NAME,
            "dev_mode": SECURITY_MODE == "dev",
            "keys_dir": KEYS_DIR,
            "agent_card": AGENT_CARD,
        },
    )
    if CAPISCIO_AVAILABLE
    else None
)

# Global event emitter (for dashboard visibility)
events: Optional[EventEmitter] = None

# Resolved SimpleGuard instance — set once during lifespan, used by middleware
_resolved_simple_guard = None


# ==============================================================================
# LangChain Tools
# ==============================================================================

@tool
def search_web(query: str) -> str:
    """Search the web for information about a topic."""
    # Simple mock search - in production, use DuckDuckGo or other search
    return f"Search results for '{query}': This is a demo search result. In production, integrate with a real search API."


@tool
def get_current_time() -> str:
    """Get the current UTC time."""
    return datetime.now(timezone.utc).isoformat()


@tool
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression."""
    try:
        # Safe eval for simple math
        allowed_names = {"abs": abs, "round": round, "min": min, "max": max}
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return str(result)
    except Exception as e:
        return f"Error: {e}"


# ==============================================================================
# LangChain Agent Setup
# ==============================================================================

def create_research_agent():
    """Create the LangChain research agent with CapiscIO trust enforcement.

    The pipe operator wires badge verification before every invocation:
        guard | agent
    """
    llm = ChatOpenAI(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0,
        api_key=OPENAI_API_KEY,
    )

    tools = [search_web, get_current_time, calculate]

    system_message = """You are a helpful research assistant. You can search the web,
    check the current time, and perform calculations.

    Always provide accurate and well-researched responses.
    When you use tools, explain what you're doing and why."""

    agent = create_react_agent(llm, tools, prompt=system_message)

    # ---------------------------------------------------------------
    # LINE 2: Pipe the guard into the agent — badge check on every call
    # ---------------------------------------------------------------
    if guard:
        return guard | agent
    return agent


# ==============================================================================
# FastAPI Application with A2A Endpoints
# ==============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    global events, _resolved_simple_guard

    # guard.identity triggers CapiscIO.connect() on first access
    identity = None
    if guard:
        try:
            identity = guard.identity
            _resolved_simple_guard = getattr(identity, "_guard", None)
            logger.info(f"🔑 Agent DID: {identity.did}")
            logger.info(f"🔐 Badge: {'acquired' if identity.badge else 'pending'}")
        except Exception as e:
            logger.warning(f"⚠️  CapiscIO identity setup failed: {e}")

    # Initialize event emitter for dashboard visibility
    events = EventEmitter(
        server_url=identity.server_url if identity else CAPISCIO_SERVER,
        api_key=identity.api_key if identity else os.environ.get("CAPISCIO_API_KEY", ""),
        agent_id=identity.agent_id if identity else "",
        agent_name=AGENT_NAME,
    )

    events.agent_started({
        "framework": "langchain",
        "version": "0.3.x",
        "port": PORT,
        "security_mode": SECURITY_MODE,
        "did": identity.did if identity else None,
    })

    logger.info(f"🚀 {AGENT_NAME} started on port {PORT}")

    yield

    if identity:
        identity.close()

    events.agent_stopped()
    events.close()
    logger.info("Agent stopped")


app = FastAPI(
    title=AGENT_NAME,
    description="A2A-compliant research agent built with LangChain",
    lifespan=lifespan,
)

# ==============================================================================
# CapiscIO Security Middleware
# The guard's identity is resolved lazily — middleware calls the lambda on
# each request, which returns the SimpleGuard after connect() has run.
# ==============================================================================
if CAPISCIO_AVAILABLE and CapiscioMiddleware and guard:
    security_config = SecurityConfig.from_env()
    app.add_middleware(
        CapiscioMiddleware,
        guard=lambda: _resolved_simple_guard,
        config=security_config,
        exclude_paths=["/.well-known/agent.json", "/health"],
    )
    logger.info("Security middleware registered")


# ==============================================================================
# A2A Agent Card Endpoint
# ==============================================================================

@app.get("/.well-known/agent.json")
async def get_agent_card():
    """Serve the A2A Agent Card (Google A2A Protocol)."""
    fallback_did = "did:web:localhost:agents:langchain"
    agent_did = fallback_did

    if guard:
        try:
            identity = guard.identity
            if getattr(identity, "did", None):
                agent_did = identity.did
        except Exception as exc:
            logger.warning(
                "Failed to resolve CapiscIO identity for agent card; using fallback DID: %s",
                exc,
            )

    return {
        **AGENT_CARD,
        "x-capiscio": {
            "did": agent_did,
            "trustLevel": "0" if SECURITY_MODE == "dev" else "1",
            "badgeEndpoint": f"{CAPISCIO_SERVER}/v1/validate",
        }
    }


# ==============================================================================
# A2A Task Endpoints
# ==============================================================================

@app.post("/tasks/send")
async def send_task(request: Request, x_capiscio_badge: Optional[str] = Header(None)):
    """Handle incoming A2A task (Google A2A Protocol)."""
    body = await request.json()
    task_id = body.get("id", str(uuid.uuid4()))

    events.emit(
        EventType.A2A_REQUEST_RECEIVED,
        {"task_id": task_id, "from_badge": x_capiscio_badge is not None},
    )

    message = body.get("message", {})
    parts = message.get("parts", [])
    text_content = ""
    for part in parts:
        if part.get("type") == "text":
            text_content += part.get("text", "")

    if not text_content:
        raise HTTPException(status_code=400, detail="No text content in message")

    # LINE 3: CapiscioCallbackHandler for dashboard observability
    callbacks = [CapiscioCallbackHandler(emitter=events)] if CapiscioCallbackHandler and events else []

    research_agent = create_research_agent()

    events.task_started(task_id, "research", {"query": text_content[:100]})

    try:
        result = await asyncio.to_thread(
            research_agent.invoke,
            {"messages": [HumanMessage(content=text_content)]},
            {"callbacks": callbacks},
        )

        # Extract output from langgraph response
        messages = result.get("messages", [])
        output = messages[-1].content if messages else "No response generated"

        events.task_completed(task_id, {"output_length": len(output)})

        # Return A2A compliant response
        return {
            "id": task_id,
            "status": {
                "state": "completed",
            },
            "artifacts": [
                {
                    "parts": [
                        {"type": "text", "text": output}
                    ]
                }
            ]
        }

    except Exception as e:
        logger.exception("Task failed")
        events.task_failed(task_id, str(e))

        return JSONResponse(
            status_code=500,
            content={
                "id": task_id,
                "status": {
                    "state": "failed",
                    "message": str(e),
                }
            }
        )


@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """Get task status (stub for A2A compliance)."""
    return {
        "id": task_id,
        "status": {"state": "unknown"},
    }


# ==============================================================================
# Health Check
# ==============================================================================

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "agent": AGENT_NAME}


# ==============================================================================
# Interactive Demo Mode
# ==============================================================================

async def demo_mode():
    """Run interactive demo if not serving HTTP."""
    global events

    print("\n" + "="*60)
    print(f"🤖 {AGENT_NAME} - Interactive Demo Mode")
    print("="*60)
    print("Type 'quit' to exit\n")

    callbacks = [CapiscioCallbackHandler(emitter=events)] if CapiscioCallbackHandler and events else []
    research_agent = create_research_agent()

    while True:
        try:
            query = input("\n🔍 Ask me anything: ").strip()
            if query.lower() in ["quit", "exit", "q"]:
                break
            if not query:
                continue

            task_id = str(uuid.uuid4())[:8]
            events.task_started(task_id, "interactive", {"query": query})

            result = research_agent.invoke(
                {"messages": [HumanMessage(content=query)]},
                {"callbacks": callbacks},
            )
            messages = result.get("messages", [])
            output = messages[-1].content if messages else "No response"

            print(f"\n📝 Response:\n{output}")
            events.task_completed(task_id, {"output_length": len(output)})

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            events.error(str(e), "interactive_error")


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
        # Interactive demo — guard.identity triggers connect()
        identity = None
        if guard:
            try:
                identity = guard.identity
                logger.info(f"🔑 Agent DID: {identity.did}")
            except Exception as e:
                logger.warning(f"⚠️  CapiscIO identity not available: {e}")

        events = EventEmitter(
            server_url=identity.server_url if identity else CAPISCIO_SERVER,
            api_key=identity.api_key if identity else os.environ.get("CAPISCIO_API_KEY", ""),
            agent_id=identity.agent_id if identity else "",
            agent_name=AGENT_NAME,
        )

        events.agent_started({
            "mode": "interactive",
            "framework": "langchain",
            "did": identity.did if identity else None,
        })

        try:
            asyncio.run(demo_mode())
        finally:
            if identity:
                identity.close()
            events.agent_stopped()
            events.close()
