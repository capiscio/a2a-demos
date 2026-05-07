# PyCon 2026 — a2a-demos Execution Plan

> **Goal**: Get `a2a-demos` to production-quality DX for PyCon US 2026 (next week).  
> **Scope**: Fix critical bugs, fill demo gaps, record 3 videos.  
> **Constraint**: RFC-009 and RFC-010 are NOT implemented — do not reference them.

---

## Context for Executing Agent

### Repository Layout

```
~/Development/CapiscIO/
├── a2a-demos/              ← THIS REPO (the demos)
├── capiscio-sdk-python/    ← Python SDK (editable dep)
├── capiscio-mcp-python/    ← MCP Guard package (editable dep)
├── langchain-capiscio/     ← LangChain integration (editable dep)
├── capiscio-core/          ← Go binary (badge CA, DID, gateway)
├── capiscio-server/        ← Backend REST API
└── capiscio-ui/            ← Dashboard frontend
```

### Dev Mode Setup

All demos should use local repos during development:

```bash
cd a2a-demos
make dev          # Installs from local repos (editable)
# OR per-demo:
./demo-one/setup.sh --local
./demo-two/setup.sh --local
./scripts/setup.sh --local
```

### Key Packages on PyPI (current published versions)

| Package | PyPI Version | Local Version |
|---------|-------------|---------------|
| `capiscio-sdk` | 2.6.0 | 2.6.0 |
| `capiscio-mcp` | 2.4.0 | 2.6.0 |
| `langchain-capiscio` | 0.1.0 | 0.1.0 |

### Working Environment

- `.env` and `.env.dev` exist locally (gitignored) with valid credentials
- Production registry: `https://registry.capisc.io`
- Dev registry: `https://dev.registry.capisc.io`
- Dashboard: `https://app.capisc.io` / `https://dev.app.capisc.io`

---

## Phase 1: Critical Fixes (Must-Do)

### 1.1 Fix Version Pins

**Problem**: `demo-one/requirements.txt` requires `capiscio-mcp[mcp,crypto]>=2.5.0` but PyPI only has 2.4.0. The `[crypto]` extra doesn't exist in the package.

**Action**:
```
# demo-one/requirements.txt — change to:
capiscio-sdk>=2.4.0
capiscio-mcp[mcp]>=2.4.0
python-dotenv>=1.0.0
httpx>=0.27.0
```

**Also check**: `demo-two/requirements.txt` for the same issue.

**Verification**: `pip install -r demo-one/requirements.txt` succeeds in a fresh venv.

---

### 1.2 Standardize Registry URLs

**Problem**: `.env.example` files inconsistently reference `dev.registry.capisc.io` vs `registry.capisc.io`. PyCon attendees should use production.

**Action**: Update ALL `.env.example` files to use production URLs:

| File | Change |
|------|--------|
| `demo-one/.env.example` | `CAPISCIO_SERVER_URL=https://registry.capisc.io` |
| `demo-two/.env.example` | `CAPISCIO_SERVER_URL=https://registry.capisc.io` |
| `.env.example` (root) | Already correct — no change |
| `mcp-demo/.env.example` | Verify it uses `https://registry.capisc.io` |

Also update the `run_demo.py` fallback defaults in both demos:
- `demo-one/agents/trusted_agent.py` line with `server_url=os.environ.get("CAPISCIO_SERVER_URL", "https://dev.registry.capisc.io")` → change default to `https://registry.capisc.io`
- Same for `demo-one/agents/untrusted_agent.py`
- Demo-two has the same agents — check and fix.

**Verification**: `grep -r "dev.registry" . --include="*.py" --include="*.env*"` returns nothing except `.env.dev`.

---

### 1.3 Fix Demo-Two Dashboard URL in run_demo.py

**Problem**: `demo-two/run_demo.py` prints `https://dev.app.capisc.io` — should be production for PyCon.

**Action**: Change all `dev.app.capisc.io` references in `demo-two/run_demo.py` to `app.capisc.io`.

---

### 1.4 Add `pyyaml` to demo-two/requirements.txt

**Problem**: `demo-two/scripts/setup_policies.py` imports `yaml` but it may not be in requirements.txt.

**Action**: Verify `pyyaml` is listed. If not, add it.

---

## Phase 2: Demo Enhancements (High-Impact)

### 2.1 Add Badge Revocation Scenario to Demo One

**Why**: RFC-008 is fully implemented but never showcased. Badge revocation is the most dramatic "security moment" we can show.

**Action**: Add Scenario 5 to `demo-one/run_demo.py`:

```python
# After Scenario 4, add:

# Scenario 5: Revoke the trusted agent's badge, then retry
scenario_header(5, "trusted (badge REVOKED)", "place_order", 1, "DENY")

# Revoke the badge via the SDK
trusted.revoke_badge()  # or call the API directly

# Small delay for propagation
await asyncio.sleep(2)

outcome, detail = await call_tool(
    trusted_badge, "place_order", {"sku": "WIDGET-A", "quantity": 1}
)
result_line(outcome, detail)
```

**Implementation notes**:
- Check `capiscio-sdk-python` for a `revoke_badge()` method on `AgentIdentity`
- If it doesn't exist, call the server API directly: `POST /v1/agents/{agent_id}/badge/revoke` with the API key header
- The guard on the MCP server should reject the revoked badge on next call
- Update the summary text at the end of run_demo.py to mention revocation

**Verification**: Run `python run_demo.py` — Scenario 5 should show DENY.

---

### 2.2 ~~Automate Policy Switching in Demo Two~~ (DECIDED: Manual Only)

**Decision**: After review, the `--auto` mode was removed. Policy switching is always manual
with clear numbered instructions for the presenter. This keeps the demo authentic — the
audience sees the real dashboard workflow.

The demo pauses between phases with:
```
ACTION REQUIRED:
  Switch to the lockdown policy in the dashboard:
    1. Open https://app.capisc.io → Policies
    2. Approve the lockdown policy proposal
    3. Wait a few seconds for the PDP bundle to refresh

  Press Enter when the lockdown policy is active...
```

---

### 2.3 Add Trust Enforcement to Agent Chain Demo

**Why**: The `--chain` flag in `demo_driver.py` shows agents calling each other, but never demonstrates trust enforcement between agents — which is the entire point of CapiscIO.

**Action**: Add a `--trust-demo` flag to `scripts/demo_driver.py`:

```python
def demo_trust_enforcement():
    """Demo where an agent rejects a request from an untrusted caller."""
    print("\n" + "="*60)
    print("🛡️  A2A TRUST ENFORCEMENT DEMO")
    print("="*60)
    print("\nThis demo shows what happens when an agent enforces trust:")
    print("  1. LangChain agent (badged) → LangGraph: ALLOWED")
    print("  2. Anonymous caller (no badge) → LangGraph: DENIED")
    print("="*60)

    # Step 1: Badged agent calls LangGraph
    print("\n📍 STEP 1: Badged agent → LangGraph (should succeed)")
    # Get the langchain agent's badge token
    langchain_card = discover_agent(AGENTS["langchain"]["url"])
    badge_token = None
    if langchain_card:
        x_capiscio = langchain_card.get("x-capiscio", {})
        # Fetch the badge from the running agent
        try:
            resp = httpx.get(f"{AGENTS['langchain']['url']}/badge", timeout=5.0)
            if resp.status_code == 200:
                badge_token = resp.json().get("badge")
        except Exception:
            pass
    
    result = send_task(AGENTS["langgraph"]["url"], "Help me reset my password", badge_token=badge_token)
    # ... show result

    # Step 2: No badge → should be denied
    print("\n📍 STEP 2: No badge → LangGraph (should be denied)")
    result = send_task(AGENTS["langgraph"]["url"], "Help me reset my password", badge_token=None)
    # ... show denial
```

**Pre-requisite**: For this to work, the LangGraph agent needs `CAPISCIO_REQUIRE_SIGNATURES=true` in its env. Add a note in the demo driver output:

```
NOTE: Set CAPISCIO_REQUIRE_SIGNATURES=true in .env before running --trust-demo
```

**Verification**: With `CAPISCIO_REQUIRE_SIGNATURES=true`, the unbadged call returns 401/403.

---

### 2.4 Upgrade LangGraph Agent to Use Real LLM

**Why**: The current keyword-matching classification (`if "bug" in message`) is embarrassingly obvious to a PyCon audience. It undermines credibility.

**Action**: Replace the `classify_request` function in `agents/langgraph-agent/main.py`:

```python
from langchain_openai import ChatOpenAI

def classify_request(state: SupportState) -> dict:
    """Classify the user's request using an LLM."""
    emit_node_start("classify_request", state)
    
    message = state["user_message"]
    
    if OPENAI_API_KEY:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=OPENAI_API_KEY)
        result = llm.invoke(
            f"Classify this customer support request into exactly one category: "
            f"technical, billing, or general. Reply with just the category word.\n\n"
            f"Request: {message}"
        )
        category = result.content.strip().lower()
        if category not in ("technical", "billing", "general"):
            category = "general"
    else:
        # Fallback to keyword matching if no LLM available
        message_lower = message.lower()
        if any(word in message_lower for word in ["bug", "error", "crash", "not working"]):
            category = "technical"
        elif any(word in message_lower for word in ["bill", "charge", "payment", "refund"]):
            category = "billing"
        else:
            category = "general"
    
    updates = {
        "category": category,
        "context": [f"Request classified as: {category}"],
    }
    emit_node_end("classify_request", updates)
    return updates
```

Also update `generate_response` to use the LLM for the final answer instead of templated text.

**Verification**: `python main.py --serve` starts successfully, and `demo_driver.py --agent langgraph` returns an LLM-generated response.

---

### 2.5 Replace Mock Search with DuckDuckGo

**Why**: "This is a demo search result" looks fake and unimpressive.

**Action**: In `agents/langchain-agent/main.py`, replace the `search_web` tool:

```python
try:
    from langchain_community.tools import DuckDuckGoSearchResults
    _ddg = DuckDuckGoSearchResults(max_results=3)
    HAS_DDG = True
except ImportError:
    HAS_DDG = False

@tool
def search_web(query: str) -> str:
    """Search the web for information about a topic."""
    if HAS_DDG:
        return _ddg.invoke(query)
    return f"[Search unavailable] Mock results for: {query}"
```

Add to `agents/langchain-agent/requirements.txt`:
```
duckduckgo-search>=6.0.0
```

**For CrewAI**: Same pattern in `agents/crewai-agent/main.py` — replace the mock `SearchTool._run()` with DuckDuckGo.

**Verification**: `python scripts/demo_driver.py --agent langchain` returns real search results.

---

### 2.6 Add `/badge` Endpoint to All Agents

**Why**: The trust enforcement demo needs to fetch a running agent's badge token. Also useful for debugging.

**Action**: Add this endpoint to each agent's FastAPI app:

```python
@app.get("/badge")
async def get_badge():
    """Return this agent's current trust badge (for A2A trust delegation)."""
    if agent and agent.badge:
        return {"badge": agent.badge, "did": agent.did}
    return JSONResponse(status_code=404, content={"error": "No badge available"})
```

Add to: `agents/langchain-agent/main.py`, `agents/crewai-agent/main.py`, `agents/langgraph-agent/main.py`.

---

## Phase 3: Polish & Presentation

### 3.1 Create Root-Level `run_all.py` for Quick Video Recording

**Why**: For video recording, you need a single command that runs a demo end-to-end with clean output.

**Action**: Create `a2a-demos/run_video.py`:

```python
#!/usr/bin/env python3
"""
Video recording helper — runs demos with clean output and timing.

Usage:
    python run_video.py demo-one      # 5 min video
    python run_video.py demo-two      # 10 min video (requires --auto env)
    python run_video.py agents        # 15 min video (requires running agents)
"""
import subprocess
import sys
import os

DEMOS = {
    "demo-one": {
        "cmd": [sys.executable, "demo-one/run_demo.py"],
        "title": "Zero to Enforcement",
        "duration": "~5 minutes",
    },
    "demo-two": {
        "cmd": [sys.executable, "demo-two/run_demo.py", "--auto"],
        "title": "Policy as Code",
        "duration": "~10 minutes",
    },
    "agents": {
        "cmd": [sys.executable, "scripts/demo_driver.py", "--chain"],
        "title": "Multi-Framework Agent Trust",
        "duration": "~15 minutes",
    },
}

def main():
    if len(sys.argv) < 2 or sys.argv[1] not in DEMOS:
        print("Usage: python run_video.py [demo-one|demo-two|agents]")
        for key, info in DEMOS.items():
            print(f"  {key:12s} — {info['title']} ({info['duration']})")
        sys.exit(1)
    
    demo = DEMOS[sys.argv[1]]
    print(f"\n{'═' * 60}")
    print(f"  🎬 Recording: {demo['title']}")
    print(f"  ⏱  Duration: {demo['duration']}")
    print(f"{'═' * 60}\n")
    
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    subprocess.run(demo["cmd"])

if __name__ == "__main__":
    main()
```

---

### 3.2 Add Makefile Targets for Demo Recording

Add to `Makefile`:

```makefile
# ─── Video recording ─────────────────────────────────────────────────────

video-one: ## Record Video 1: Zero to Enforcement
	$(PYTHON) run_video.py demo-one

video-two: ## Record Video 2: Policy as Code
	$(PYTHON) run_video.py demo-two

video-agents: ## Record Video 3: Multi-Framework Agent Trust
	$(PYTHON) run_video.py agents
```

---

### 3.3 Update README PyCon Banner

The repo is currently on branch `feature/readme-pycon-banner`. Ensure the README has:
- PyCon US 2026 date and booth/talk info
- Direct link to setup instructions
- "Try it in 5 minutes" quick path

---

### 3.4 Remove Stale `__pycache__` and `.pyc` Files from Git

**Problem**: The tree shows `__pycache__/` directories and `.pyc` files. While `.gitignore` should catch them, verify none are tracked.

**Action**:
```bash
git ls-files | grep -E '__pycache__|\.pyc$'
# If any results: git rm --cached <files>
```

---

## Phase 4: Release Workflow (After Testing)

Once all demos work with local repos:

### 4.1 Merge Pending PRs

These PRs need to be merged before release:
- `capiscio-sdk-python` PR #62: `feat: connect() falls back to CAPISCIO_API_KEY env var`
- `capiscio-sdk-python` PR #61: `feat: surface structured rejection fields (RFC-008 B8)`
- `capiscio-mcp-python` PR #22: `feat: emit policy_enforced events on guard deny (RFC-008 B9)`

### 4.2 Publish Packages

Order matters:
1. `capiscio-sdk` → bump to 2.7.0 (or 3.0.0)
2. `capiscio-mcp` → bump to 2.7.0 (depends on sdk)
3. `langchain-capiscio` → bump to 0.2.0 (depends on sdk)

### 4.3 Update Demo Requirements to Published Versions

```bash
# After publishing, update all requirements.txt files:
sed -i '' 's/capiscio-sdk>=.*/capiscio-sdk>=2.7.0/' demo-one/requirements.txt
sed -i '' 's/capiscio-mcp.*/capiscio-mcp[mcp]>=2.7.0/' demo-one/requirements.txt
# ... repeat for demo-two, agents/*
```

### 4.4 Final Verification

```bash
# Test with PyPI versions (no --local)
make clean
make install
make demo-one
make demo-two
# Start agents and run demo_driver
```

### 4.5 Tag and Release

```bash
git tag v1.0.0-pycon
git push origin v1.0.0-pycon
```

---

## Video Script Outlines

### Video 1: "Zero to Trust in 5 Minutes" (Demo One)

1. **Hook** (30s): "What if adding security to your MCP server was as easy as adding HTTPS to a website?"
2. **Setup** (30s): Show `.env`, explain API key from dashboard
3. **Run Demo** (3 min): 
   - Show the server code: 3 tools, one `@guard` decorator each
   - Show the agent code: one line `CapiscIO.connect()`
   - Run `python run_demo.py` — watch ALLOW/ALLOW/ALLOW/DENY
   - Explain: badge = proof of identity, trust level = access control
4. **Revocation** (1 min): Show Scenario 5 — revoke badge, immediate DENY
5. **Outro** (30s): "One decorator. Zero infrastructure. capisc.io/pycon"

### Video 2: "Policy as Code — No Deploy Required" (Demo Two)

1. **Hook** (30s): "Your CISO calls at 2 AM. Lock down all AI agents. Now."
2. **Baseline** (1 min): Same setup as Demo One — show normal operation
3. **Lockdown** (2 min): Switch policy → EVERYTHING denied. No code change. No deploy.
4. **Selective** (2 min): A "public" tool becomes restricted. Platform admin overrides developer defaults.
5. **Recovery** (1 min): Switch back to baseline — normal operation restored
6. **Key insight** (30s): "Developers set defaults. Platform admins set guardrails. Both win."

### Video 3: "Multi-Framework Agent Trust" (Agents)

1. **Hook** (30s): "3 agents. 3 frameworks. 1 trust layer."
2. **Show agents** (2 min): LangChain, CrewAI, LangGraph — each has `CapiscIO.connect()`
3. **Start & discover** (2 min): All 3 start, get DIDs, serve Agent Cards
4. **Chain demo** (3 min): Research → Content → Support pipeline
5. **Trust enforcement** (3 min): Enable `REQUIRE_SIGNATURES=true`, show unbadged caller gets rejected
6. **Dashboard** (2 min): Show real-time events flowing through all 3 agents
7. **Outro** (30s): "Every framework. Every protocol. One trust layer."

---

## Execution Order

```
Phase 1 (30 min) — Critical fixes
  1.1 → 1.2 → 1.3 → 1.4
  Verify: make dev && make demo-one && make demo-two

Phase 2 (2-3 hours) — Enhancements
  2.6 → 2.4 → 2.5 → 2.1 → 2.2 → 2.3
  Verify: full demo runs end-to-end

Phase 3 (1 hour) — Polish
  3.1 → 3.2 → 3.3 → 3.4
  Verify: make video-one works

Phase 4 (after all testing passes) — Release
  4.1 → 4.2 → 4.3 → 4.4 → 4.5
```

---

## Success Criteria

- [ ] `make dev` completes without errors
- [ ] `python demo-one/run_demo.py` shows 5 scenarios (including revocation) with correct ALLOW/DENY
- [ ] `python demo-two/run_demo.py --auto` runs all 3 phases without manual intervention
- [ ] All 3 agents start with `--serve` and respond to `demo_driver.py`
- [ ] `demo_driver.py --trust-demo` shows ALLOW then DENY
- [ ] LangGraph agent uses LLM for classification (not keyword matching)
- [ ] LangChain agent returns real search results (DuckDuckGo)
- [ ] No references to `dev.registry.capisc.io` in any `.py` or `.env.example` file
- [ ] `grep -r "sk_live\|sk_proj\|OPENAI_API_KEY=sk" . --include="*.py" --include="*.md"` returns nothing
- [ ] `make lint` passes
- [ ] `make test` passes (syntax check)
