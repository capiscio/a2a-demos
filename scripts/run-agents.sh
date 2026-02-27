#!/usr/bin/env bash
#
# Run all agents in separate tmux panes (or sequentially if no tmux)
#
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"

# Check for tmux
if command -v tmux &> /dev/null && [ -z "$TMUX" ]; then
    echo "Starting agents in tmux session..."
    
    # Create new tmux session
    tmux new-session -d -s a2a-demos -n agents
    
    # Split into 3 panes
    tmux split-window -h -t a2a-demos:agents
    tmux split-window -v -t a2a-demos:agents.0
    
    # Run agents in each pane (--serve for HTTP mode)
    tmux send-keys -t a2a-demos:agents.0 "cd $SCRIPT_DIR/agents/langchain-agent && source .venv/bin/activate && python main.py --serve" Enter
    tmux send-keys -t a2a-demos:agents.1 "cd $SCRIPT_DIR/agents/crewai-agent && source .venv/bin/activate && python main.py --serve" Enter
    tmux send-keys -t a2a-demos:agents.2 "cd $SCRIPT_DIR/agents/langgraph-agent && source .venv/bin/activate && python main.py --serve" Enter
    
    # Attach to session
    tmux attach -t a2a-demos
else
    # No tmux or already in tmux - guide user
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║  Run agents in separate terminals (--serve for HTTP mode)  ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Terminal 1 (LangChain - port 8001):"
    echo "  cd agents/langchain-agent && source .venv/bin/activate"
    echo "  python main.py --serve"
    echo ""
    echo "Terminal 2 (CrewAI - port 8002):"
    echo "  cd agents/crewai-agent && source .venv/bin/activate"
    echo "  python main.py --serve"
    echo ""
    echo "Terminal 3 (LangGraph - port 8003):"
    echo "  cd agents/langgraph-agent && source .venv/bin/activate"
    echo "  python main.py --serve"
    echo ""
    echo "Then run the demo driver:"
    echo "  python scripts/demo_driver.py"
    echo ""
    echo "Tip: Install tmux for automatic parallel execution"
fi
