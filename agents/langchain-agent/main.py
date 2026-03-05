"""
LangChain Research Agent with CapiscIO Security

This agent demonstrates:
1. A2A-compliant Agent Card serving
2. Automatic badge management via CapiscIO.connect()
3. Real-time event emission to CapiscIO dashboard
4. Tool-calling agent for research tasks
5. "Let's Encrypt" style one-liner identity setup
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

# CapiscIO SDK - "Let's Encrypt" style agent identity
try:
    from capiscio_sdk import CapiscIO, SecurityConfig
    from capiscio_sdk.connect import AgentIdentity
    from capiscio_sdk.integrations.fastapi import CapiscioMiddleware
    from capiscio_sdk.simple_guard import SimpleGuard
    CAPISCIO_SDK_AVAILABLE = True
except ImportError:
    CAPISCIO_SDK_AVAILABLE = False
    CapiscIO = None
    AgentIdentity = None
    SecurityConfig = None
    CapiscioMiddleware = None
    SimpleGuard = None

# LangChain imports
from langchain_core.callbacks import BaseCallbackHandler
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

# Security mode: 'dev' (self-signed, SDK handles everything) or 'ca' (registry-issued badges)
SECURITY_MODE = os.environ.get("SECURITY_MODE", "ca")  # Default to production CA mode

# Global agent identity (from CapiscIO.connect())
agent: Optional["AgentIdentity"] = None

# A2A Agent Card (static parts - stored in registry and served at /.well-known/agent.json)
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

# Global event emitter (for framework-specific events)
events: Optional[EventEmitter] = None


class CapiscioCallbackHandler(BaseCallbackHandler):
    """LangChain callback handler that emits events to CapiscIO."""

    def __init__(self, emitter: EventEmitter):
        self.emitter = emitter

    def on_chain_start(self, serialized, inputs, **kwargs):
        chain_name = serialized.get("name", "unknown")
        self.emitter.emit(
            EventType.LANGCHAIN_CHAIN_START,
            {"chain": chain_name, "inputs": str(inputs)[:200]},
        )

    def on_chain_end(self, outputs, **kwargs):
        self.emitter.emit(
            EventType.LANGCHAIN_CHAIN_END,
            {"outputs": str(outputs)[:200]},
        )

    def on_llm_start(self, serialized, prompts, **kwargs):
        model = serialized.get("name", "unknown")
        self.emitter.emit(
            EventType.LANGCHAIN_LLM_START,
            {"model": model, "prompt_count": len(prompts)},
        )

    def on_llm_end(self, response, **kwargs):
        self.emitter.emit(
            EventType.LANGCHAIN_LLM_END,
            {"generations": len(response.generations) if response.generations else 0},
        )

    def on_tool_start(self, serialized, input_str, **kwargs):
        tool_name = serialized.get("name", "unknown")
        self.emitter.emit(
            EventType.LANGCHAIN_TOOL_START,
            {"tool": tool_name, "input": str(input_str)[:200]},
        )

    def on_tool_end(self, output, **kwargs):
        self.emitter.emit(
            EventType.LANGCHAIN_TOOL_END,
            {"output": str(output)[:200]},
        )

    def on_tool_error(self, error, **kwargs):
        self.emitter.error(
            f"Tool error: {error}",
            error_type="tool_error",
        )


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

def create_research_agent(callback_handler: CapiscioCallbackHandler):
    """Create the LangChain research agent using LangGraph."""

    # Initialize LLM
    llm = ChatOpenAI(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0,
        api_key=OPENAI_API_KEY,
    )

    # Define tools
    tools = [search_web, get_current_time, calculate]

    # System message for the agent
    system_message = """You are a helpful research assistant. You can search the web,
    check the current time, and perform calculations.

    Always provide accurate and well-researched responses.
    When you use tools, explain what you're doing and why."""

    # Create the agent using langgraph prebuilt
    agent = create_react_agent(llm, tools, prompt=system_message)

    return agent


# ==============================================================================
# FastAPI Application with A2A Endpoints
# ==============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    global events, agent

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

    # Emit startup event
    events.agent_started({
        "framework": "langchain",
        "version": "0.3.x",
        "port": PORT,
        "security_mode": SECURITY_MODE,
        "did": agent.did if agent else None,
    })

    logger.info(f"🚀 {AGENT_NAME} started on port {PORT}")
    logger.info(f"📊 Events visible at {CAPISCIO_SERVER.replace(':8080', ':3000')}/events")

    yield

    # Close agent (stops badge renewal, cleans up)
    if agent:
        agent.close()

    # Emit shutdown event
    events.agent_stopped()
    events.close()
    logger.info("Agent stopped")


app = FastAPI(
    title=AGENT_NAME,
    description="A2A-compliant research agent built with LangChain",
    lifespan=lifespan,
)

# ==============================================================================
# CapiscIO Security Middleware (SDK-based enforcement)
# Must be added at module level BEFORE app starts
# ==============================================================================
if CAPISCIO_SDK_AVAILABLE and CapiscioMiddleware and SimpleGuard:
    # Load security config from environment
    security_config = SecurityConfig.from_env()
    logger.info(f"Security config: fail_mode={security_config.fail_mode}, "
                f"require_signatures={security_config.downstream.require_signatures}")

    # Create guard for middleware (dev_mode auto-generates keys when no agent-card.json)
    _guard = SimpleGuard(
        dev_mode=(SECURITY_MODE == "dev"),
        base_dir=os.path.dirname(os.path.abspath(__file__)),
    )
    app.add_middleware(
        CapiscioMiddleware,
        guard=_guard,
        config=security_config,
        exclude_paths=["/.well-known/agent.json", "/health"],
    )
    logger.info("🛡️  Security middleware enabled at module level")


# ==============================================================================
# A2A Agent Card Endpoint
# ==============================================================================

@app.get("/.well-known/agent.json")
async def get_agent_card():
    """
    Serve the A2A Agent Card (Google A2A Protocol).

    This endpoint is discovered by other agents to understand our capabilities.
    """
    agent_did = agent.did if agent else "did:web:localhost:agents:langchain"

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
    """
    Handle incoming A2A task (Google A2A Protocol).

    In production, validate the X-Capiscio-Badge header.
    """
    body = await request.json()
    task_id = body.get("id", str(uuid.uuid4()))

    # Emit task received event
    events.emit(
        EventType.A2A_REQUEST_RECEIVED,
        {"task_id": task_id, "from_badge": x_capiscio_badge is not None},
    )

    # Extract message content
    message = body.get("message", {})
    parts = message.get("parts", [])
    text_content = ""
    for part in parts:
        if part.get("type") == "text":
            text_content += part.get("text", "")

    if not text_content:
        raise HTTPException(status_code=400, detail="No text content in message")

    # Create callback handler
    callback = CapiscioCallbackHandler(events)

    # Create agent and run
    agent = create_research_agent(callback)

    events.task_started(task_id, "research", {"query": text_content[:100]})

    try:
        result = await asyncio.to_thread(
            agent.invoke,
            {"messages": [HumanMessage(content=text_content)]}
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
    print("\n📊 Events visible at: https://app.capisc.io/events")
    print("Type 'quit' to exit\n")

    callback = CapiscioCallbackHandler(events)
    agent = create_research_agent(callback)

    while True:
        try:
            query = input("\n🔍 Ask me anything: ").strip()
            if query.lower() in ["quit", "exit", "q"]:
                break
            if not query:
                continue

            task_id = str(uuid.uuid4())[:8]
            events.task_started(task_id, "interactive", {"query": query})

            result = agent.invoke({"messages": [HumanMessage(content=query)]})
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
        # Run as HTTP server
        uvicorn.run(app, host="0.0.0.0", port=args.port)
    else:
        # Run interactive demo
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

        # Initialize events for demo mode
        events = EventEmitter(
            server_url=agent.server_url if agent else CAPISCIO_SERVER,
            api_key=agent.api_key if agent else os.environ.get("CAPISCIO_API_KEY", ""),
            agent_id=agent.agent_id if agent else "",
            agent_name=AGENT_NAME,
        )

        events.agent_started({
            "mode": "interactive",
            "framework": "langchain",
            "did": agent.did if agent else None,
        })

        try:
            asyncio.run(demo_mode())
        finally:
            if agent:
                agent.close()
            events.agent_stopped()
            events.close()
