"""
CrewAI Multi-Agent System with CapiscIO Security

This demonstrates a multi-agent crew with:
1. "Let's Encrypt" style one-liner identity setup
2. Automatic badge management via CapiscIO.connect()
3. Real-time event emission showing individual agent activity
"""

import asyncio
import logging
import os
import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

# Add shared module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from capiscio_events import EventEmitter, EventSeverity, EventType

# CapiscIO SDK - "Let's Encrypt" style agent identity
try:
    from capiscio_sdk import CapiscIO, SecurityConfig
    from capiscio_sdk.connect import AgentIdentity
    from capiscio_sdk.integrations.fastapi import CapiscioMiddleware
    CAPISCIO_SDK_AVAILABLE = True
except ImportError:
    CAPISCIO_SDK_AVAILABLE = False
    CapiscIO = None
    AgentIdentity = None
    SecurityConfig = None
    CapiscioMiddleware = None

# CrewAI imports
from crewai import Agent, Crew, Process, Task
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("crewai-agent")

# Load environment
load_dotenv()

# Configuration
AGENT_NAME = "CrewAI Content Crew"
CAPISCIO_SERVER = os.environ.get("CAPISCIO_SERVER_URL", "https://registry.capisc.io")
PORT = int(os.environ.get("CREWAI_AGENT_PORT", "8002"))
SECURITY_MODE = os.environ.get("SECURITY_MODE", "ca")  # 'dev' or 'ca'

# Global instances
events: Optional[EventEmitter] = None
agent: Optional["AgentIdentity"] = None

# A2A Agent Card (static parts - stored in registry and served at /.well-known/agent.json)
AGENT_CARD = {
    "name": AGENT_NAME,
    "description": "A content creation crew with researcher, writer, and editor agents",
    "url": f"http://localhost:{PORT}",
    "version": "1.0.0",
    "capabilities": {
        "streaming": False,
        "pushNotifications": False,
    },
    "skills": [
        {
            "id": "create_content",
            "name": "Content Creation",
            "description": "Research, write, and edit content on any topic",
        }
    ],
    "authentication": {"schemes": ["capiscio-badge"]},
}


# ==============================================================================
# Custom Tools for CrewAI
# ==============================================================================

class SearchInput(BaseModel):
    """Input schema for search tool."""
    query: str = Field(description="Search query")


class SearchTool(BaseTool):
    """Web search tool that emits events."""
    name: str = "search_web"
    description: str = "Search the web for information"
    args_schema: type[BaseModel] = SearchInput
    
    def _run(self, query: str) -> str:
        if events:
            events.tool_invoked("search_web", {"query": query})
        
        # Mock search result
        result = f"Research findings for '{query}': This is demo content. In production, integrate real search."
        
        if events:
            events.tool_completed("search_web", {"result_length": len(result)})
        
        return result


class WriteInput(BaseModel):
    """Input schema for writing tool."""
    content: str = Field(description="Content to write/process")


class WritingTool(BaseTool):
    """Writing assistance tool."""
    name: str = "enhance_writing"
    description: str = "Enhance and polish written content"
    args_schema: type[BaseModel] = WriteInput
    
    def _run(self, content: str) -> str:
        if events:
            events.tool_invoked("enhance_writing", {"content_length": len(content)})
        
        # Mock enhancement
        result = f"Enhanced content:\n\n{content}\n\n[Content has been polished and improved]"
        
        if events:
            events.tool_completed("enhance_writing", {"result_length": len(result)})
        
        return result


# ==============================================================================
# CrewAI Agent and Task Definitions
# ==============================================================================

def create_content_crew(topic: str, trace_id: str) -> Crew:
    """Create a content creation crew for the given topic."""
    
    # Define agents
    researcher = Agent(
        role="Senior Research Analyst",
        goal=f"Gather comprehensive information about {topic}",
        backstory="""You are an expert researcher with years of experience
        in gathering and analyzing information from various sources.
        You excel at finding relevant, accurate data.""",
        tools=[SearchTool()],
        verbose=True,
    )
    
    writer = Agent(
        role="Content Writer",
        goal=f"Create engaging content about {topic}",
        backstory="""You are a skilled writer who can transform complex
        information into clear, engaging content that resonates with readers.""",
        tools=[WritingTool()],
        verbose=True,
    )
    
    editor = Agent(
        role="Editor",
        goal="Review and polish content for quality and clarity",
        backstory="""You are a meticulous editor with an eye for detail.
        You ensure all content is clear, accurate, and professionally written.""",
        verbose=True,
    )
    
    # Define tasks
    research_task = Task(
        description=f"""Research the topic: {topic}
        
        Gather key information, statistics, and insights.
        Focus on accuracy and relevance.""",
        expected_output="A comprehensive research brief with key findings",
        agent=researcher,
    )
    
    writing_task = Task(
        description=f"""Write an engaging article about {topic}
        
        Use the research provided to create compelling content.
        Make it informative and accessible.""",
        expected_output="A well-written article draft",
        agent=writer,
        context=[research_task],
    )
    
    editing_task = Task(
        description="""Review and edit the article draft
        
        Check for clarity, accuracy, and flow.
        Polish the content for publication.""",
        expected_output="A polished, publication-ready article",
        agent=editor,
        context=[writing_task],
    )
    
    # Create crew with event callbacks
    crew = Crew(
        agents=[researcher, writer, editor],
        tasks=[research_task, writing_task, editing_task],
        process=Process.sequential,
        verbose=True,
    )
    
    return crew


def run_crew_with_events(topic: str) -> str:
    """Run the crew and emit events throughout execution."""
    trace_id = events.new_trace()
    task_id = str(uuid.uuid4())[:8]
    
    # Emit crew start
    events.emit(
        EventType.CREWAI_CREW_START,
        {"topic": topic, "agents": ["researcher", "writer", "editor"]},
        trace_id=trace_id,
    )
    
    events.task_started(task_id, "content_creation", {"topic": topic})
    
    try:
        # Create and run crew
        crew = create_content_crew(topic, trace_id)
        
        # Emit agent events as crew runs
        events.emit(
            EventType.CREWAI_AGENT_START,
            {"agent": "researcher", "role": "Senior Research Analyst"},
        )
        
        result = crew.kickoff()
        
        # Emit completion events
        events.emit(
            EventType.CREWAI_CREW_END,
            {"success": True, "output_length": len(str(result))},
        )
        
        events.task_completed(task_id, {"topic": topic})
        
        return str(result)
    
    except Exception as e:
        events.emit(
            EventType.CREWAI_CREW_END,
            {"success": False, "error": str(e)},
            severity=EventSeverity.ERROR,
        )
        events.task_failed(task_id, str(e))
        raise


# ==============================================================================
# FastAPI Application
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
            
            # Add SDK middleware for badge enforcement
            if CapiscioMiddleware and hasattr(agent, '_guard') and agent._guard:
                security_config = SecurityConfig.from_env()
                app.add_middleware(
                    CapiscioMiddleware,
                    guard=agent._guard,
                    config=security_config,
                    exclude_paths=["/.well-known/agent.json", "/health"],
                )
                logger.info(f"🛡️  Security middleware enabled (require_signatures={security_config.downstream.require_signatures})")
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
        "framework": "crewai",
        "mode": SECURITY_MODE,
        "agents": ["researcher", "writer", "editor"],
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
    description="A2A-compliant multi-agent crew built with CrewAI",
    lifespan=lifespan,
)


@app.get("/.well-known/agent.json")
async def get_agent_card():
    """Serve A2A Agent Card."""
    agent_did = agent.did if agent else "did:web:localhost:agents:crewai"
    
    return {
        **AGENT_CARD,
        "x-capiscio": {
            "did": agent_did,
            "trustLevel": "0" if SECURITY_MODE == "dev" else "1",
            "badgeEndpoint": f"{CAPISCIO_SERVER}/v1/validate",
        }
    }


@app.post("/tasks/send")
async def send_task(request: Request, x_capiscio_badge: Optional[str] = Header(None)):
    """Handle incoming A2A task."""
    body = await request.json()
    task_id = body.get("id", str(uuid.uuid4()))
    
    events.emit(
        EventType.A2A_REQUEST_RECEIVED,
        {"task_id": task_id, "authenticated": x_capiscio_badge is not None},
    )
    
    # Extract topic from message
    message = body.get("message", {})
    parts = message.get("parts", [])
    topic = ""
    for part in parts:
        if part.get("type") == "text":
            topic += part.get("text", "")
    
    if not topic:
        raise HTTPException(status_code=400, detail="No topic provided")
    
    try:
        result = await asyncio.to_thread(run_crew_with_events, topic)
        
        return {
            "id": task_id,
            "status": {"state": "completed"},
            "artifacts": [
                {"parts": [{"type": "text", "text": result}]}
            ]
        }
    
    except Exception as e:
        logger.exception("Crew execution failed")
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
    print("\n📊 Events visible at: http://localhost:3000/events")
    print("Type 'quit' to exit\n")
    
    while True:
        try:
            topic = input("\n📝 Enter a topic for the crew: ").strip()
            if topic.lower() in ["quit", "exit", "q"]:
                break
            if not topic:
                continue
            
            print(f"\n🚀 Starting crew to create content about: {topic}")
            print("Watch the dashboard for real-time agent activity!\n")
            
            result = run_crew_with_events(topic)
            
            print("\n" + "="*60)
            print("📄 FINAL OUTPUT")
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
        events.agent_started({"mode": "interactive", "framework": "crewai", "did": agent.did if agent else None})
        
        try:
            asyncio.run(demo_mode())
        finally:
            if agent:
                agent.close()
            events.agent_stopped()
            events.close()
