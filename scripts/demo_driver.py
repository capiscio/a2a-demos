#!/usr/bin/env python3
"""
A2A Demo Driver - Send Tasks Between Agents

This script demonstrates agent-to-agent communication by:
1. Discovering agents via their /.well-known/agent.json endpoints
2. Sending A2A tasks to each agent
3. Showing real-time results

Watch the CapiscIO dashboard at https://app.capisc.io/events
to see event streams as agents process tasks!
"""

import argparse
import json
import sys
import time
import uuid
from typing import Optional

import httpx

# Agent endpoints (default ports)
AGENTS = {
    "langchain": {
        "name": "LangChain Research Agent",
        "url": "http://localhost:8001",
        "demo_task": "What is the current time and calculate 42 * 17?",
    },
    "crewai": {
        "name": "CrewAI Content Crew",
        "url": "http://localhost:8002",
        "demo_task": "Write a short blog post about AI agent security",
    },
    "langgraph": {
        "name": "LangGraph Support Agent",
        "url": "http://localhost:8003",
        "demo_task": "I was charged twice for my subscription last month",
    },
}


def discover_agent(base_url: str) -> Optional[dict]:
    """Fetch the agent card from /.well-known/agent.json"""
    try:
        resp = httpx.get(f"{base_url}/.well-known/agent.json", timeout=5.0)
        if resp.status_code == 200:
            return resp.json()
        print(f"  ⚠️  Agent card returned {resp.status_code}")
        return None
    except httpx.ConnectError:
        print(f"  ❌ Agent not running at {base_url}")
        return None
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return None


def send_task(base_url: str, message: str, badge_token: Optional[str] = None) -> dict:
    """Send an A2A task to an agent."""
    task_id = str(uuid.uuid4())
    
    payload = {
        "id": task_id,
        "message": {
            "role": "user",
            "parts": [{"type": "text", "text": message}],
        },
    }
    
    headers = {"Content-Type": "application/json"}
    if badge_token:
        headers["X-Capiscio-Badge"] = badge_token
    
    resp = httpx.post(
        f"{base_url}/tasks/send",
        json=payload,
        headers=headers,
        timeout=120.0,  # Allow time for LLM calls
    )
    
    return resp.json()


def print_agent_card(card: dict):
    """Pretty print agent card info."""
    print(f"  📛 Name: {card.get('name')}")
    print(f"  📝 Description: {card.get('description', 'N/A')[:60]}...")
    
    x_capiscio = card.get("x-capiscio", {})
    if x_capiscio:
        print(f"  🔑 DID: {x_capiscio.get('did', 'N/A')[:50]}...")
        print(f"  🏷️  Trust Level: {x_capiscio.get('trustLevel', '?')}")
    
    skills = card.get("skills", [])
    if skills:
        print(f"  🛠️  Skills: {', '.join(s.get('name', s.get('id')) for s in skills)}")


def demo_single_agent(agent_key: str, custom_task: Optional[str] = None):
    """Demo a single agent."""
    agent = AGENTS.get(agent_key)
    if not agent:
        print(f"❌ Unknown agent: {agent_key}")
        print(f"   Available: {', '.join(AGENTS.keys())}")
        return
    
    print(f"\n{'='*60}")
    print(f"🤖 {agent['name']}")
    print(f"{'='*60}")
    
    # Discover
    print(f"\n📡 Discovering agent at {agent['url']}...")
    card = discover_agent(agent["url"])
    if not card:
        return
    
    print_agent_card(card)
    
    # Send task
    task = custom_task or agent["demo_task"]
    print(f"\n📤 Sending task: \"{task[:50]}{'...' if len(task) > 50 else ''}\"")
    print("   (Watch https://app.capisc.io/events for live events!)")
    
    start = time.time()
    try:
        result = send_task(agent["url"], task)
        elapsed = time.time() - start
        
        status = result.get("status", {})
        state = status.get("state", "unknown")
        
        if state == "completed":
            print(f"\n✅ Task completed in {elapsed:.1f}s")
            artifacts = result.get("artifacts", [])
            if artifacts:
                for artifact in artifacts:
                    for part in artifact.get("parts", []):
                        if part.get("type") == "text":
                            text = part.get("text", "")
                            print(f"\n📋 Response:\n{'-'*40}")
                            # Truncate long responses
                            if len(text) > 500:
                                print(text[:500] + "\n... (truncated)")
                            else:
                                print(text)
        else:
            print(f"\n❌ Task failed: {status.get('message', state)}")
            
    except httpx.ReadTimeout:
        print("\n⏱️  Task timed out after 120s")
    except Exception as e:
        print(f"\n❌ Error: {e}")


def demo_all_agents():
    """Run demo tasks on all agents."""
    print("\n" + "="*60)
    print("🎭 A2A DEMO: Agent-to-Agent Communication")
    print("="*60)
    print("\nThis demo will:")
    print("  1. Discover each agent's capabilities")
    print("  2. Send a demo task to each agent")
    print("  3. Display the results")
    print("\n👀 Watch events live at: https://app.capisc.io/events")
    print("="*60)
    
    for key in AGENTS:
        demo_single_agent(key)
        print()


def demo_chain():
    """Demo agents calling each other in a chain."""
    print("\n" + "="*60)
    print("🔗 A2A CHAIN DEMO: Research → Content → Support")
    print("="*60)
    print("\nThis demo shows a realistic workflow:")
    print("  1. LangChain researches a topic")
    print("  2. CrewAI creates content from the research")
    print("  3. LangGraph handles support questions about the content")
    print("\n👀 Watch events live at: https://app.capisc.io/events")
    print("="*60)
    
    # Step 1: Research
    print("\n📍 STEP 1: Research with LangChain")
    print("-"*40)
    langchain = AGENTS["langchain"]
    research_task = "Research the latest trends in AI agent security and trust frameworks"
    
    card = discover_agent(langchain["url"])
    if not card:
        print("❌ LangChain agent not available, stopping chain")
        return
    
    print(f"📤 Task: \"{research_task[:50]}...\"")
    try:
        result = send_task(langchain["url"], research_task)
        research_output = ""
        if result.get("status", {}).get("state") == "completed":
            for artifact in result.get("artifacts", []):
                for part in artifact.get("parts", []):
                    if part.get("type") == "text":
                        research_output = part.get("text", "")
            print(f"✅ Research complete ({len(research_output)} chars)")
        else:
            print("❌ Research failed")
            return
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # Step 2: Content
    print("\n📍 STEP 2: Create Content with CrewAI")
    print("-"*40)
    crewai = AGENTS["crewai"]
    
    card = discover_agent(crewai["url"])
    if not card:
        print("❌ CrewAI agent not available, stopping chain")
        return
    
    content_task = f"Based on this research, write a compelling blog post:\n\n{research_output[:500]}"
    print("📤 Task: Create blog post from research...")
    try:
        result = send_task(crewai["url"], content_task)
        content_output = ""
        if result.get("status", {}).get("state") == "completed":
            for artifact in result.get("artifacts", []):
                for part in artifact.get("parts", []):
                    if part.get("type") == "text":
                        content_output = part.get("text", "")
            print(f"✅ Content created ({len(content_output)} chars)")
        else:
            print("❌ Content creation failed")
            return
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # Step 3: Support
    print("\n📍 STEP 3: Support Query with LangGraph")
    print("-"*40)
    langgraph = AGENTS["langgraph"]
    
    card = discover_agent(langgraph["url"])
    if not card:
        print("❌ LangGraph agent not available, stopping chain")
        return
    
    support_task = "I read your blog post about AI security but I'm confused about how trust levels work. Can you help?"
    print(f"📤 Task: \"{support_task[:50]}...\"")
    try:
        result = send_task(langgraph["url"], support_task)
        if result.get("status", {}).get("state") == "completed":
            print("✅ Support response generated")
            for artifact in result.get("artifacts", []):
                for part in artifact.get("parts", []):
                    if part.get("type") == "text":
                        print(f"\n📋 Support Response:\n{'-'*40}")
                        print(part.get("text", "")[:500])
        else:
            print("❌ Support query failed")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "="*60)
    print("🎉 Chain demo complete!")
    print("   Check https://app.capisc.io/events for the full event trace")
    print("="*60)


def main():
    parser = argparse.ArgumentParser(
        description="A2A Demo Driver - Send tasks between agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python demo_driver.py                    # Demo all agents
  python demo_driver.py --agent langchain  # Demo single agent
  python demo_driver.py --chain            # Demo agent chain
  python demo_driver.py --agent crewai --task "Write about Python"
        """,
    )
    parser.add_argument(
        "--agent",
        choices=list(AGENTS.keys()),
        help="Demo a specific agent",
    )
    parser.add_argument(
        "--task",
        help="Custom task to send (use with --agent)",
    )
    parser.add_argument(
        "--chain",
        action="store_true",
        help="Run the agent chain demo",
    )
    parser.add_argument(
        "--discover",
        action="store_true",
        help="Only discover agents, don't send tasks",
    )
    
    args = parser.parse_args()
    
    if args.discover:
        print("\n🔍 Discovering agents...\n")
        for key, agent in AGENTS.items():
            print(f"📡 {key}: {agent['url']}")
            card = discover_agent(agent["url"])
            if card:
                print_agent_card(card)
            print()
        return
    
    if args.chain:
        demo_chain()
    elif args.agent:
        demo_single_agent(args.agent, args.task)
    else:
        demo_all_agents()


if __name__ == "__main__":
    main()
