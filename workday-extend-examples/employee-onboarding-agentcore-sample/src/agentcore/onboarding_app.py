# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Strands-based AgentCore orchestration app for Employee Onboarding.

This is the main agent file — start reading here. It wires up:
- A Strands Agent with Claude Haiku 4.5 and a tool-use system prompt
- MCP tool discovery from the AgentCore Gateway
- A streaming SSE endpoint for the AgentCore Runtime

Supporting modules (read these after understanding the main flow):
- gateway_auth.py  — Cognito OAuth2 token acquisition for MCP calls
- tool_trace.py    — captures tool calls and formats the ToolTrace section
- response_parser.py — parses the tagged Reasoning[]/Result[] output

Environment variables (set via .env or injected by deploy.sh --env):
- AGENTCORE_MCP_URL or GATEWAY_URL: Gateway MCP endpoint (https URL)
- COGNITO_*: OAuth2 credentials for gateway authentication
- MODEL_ID: Bedrock model ID (default: Claude Haiku 4.5)
- AGENT_USE_HR_TOOLS: set to 'false' to run without tools (teaching mode)
"""

import asyncio
import atexit
import os
import sys
from pathlib import Path
from typing import Any, List, Optional

from dotenv import dotenv_values

# Strands / AgentCore imports
from strands import Agent
from strands.agent.conversation_manager import SlidingWindowConversationManager
from strands.models import BedrockModel
from strands.telemetry import StrandsTelemetry
from strands.types.exceptions import ModelThrottledException

from bedrock_agentcore import BedrockAgentCoreApp
from bedrock_agentcore.runtime.context import RequestContext

# In the container, only this directory is on sys.path. In the repo layout,
# we need to add it explicitly so bare imports (response_parser, gateway_auth,
# tool_trace) work in both contexts.
_this_dir = Path(__file__).resolve().parent
if str(_this_dir) not in sys.path:
    sys.path.insert(0, str(_this_dir))

from gateway_auth import get_gateway_headers
from tool_trace import attach_tool_trace, format_tool_trace


# --------------------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------------------
# ┌─────────────────────────────────────────────────────────────────────────────┐
# │ LEARNING CHECKPOINT 1: Environment & Model Configuration                    │
# │                                                                             │
# │ The agent needs three things from the environment:                          │
# │   1. A Gateway URL (AGENTCORE_MCP_URL) — where to discover MCP tools       │
# │   2. Cognito credentials (COGNITO_*) — to authenticate MCP calls           │
# │   3. A model ID (MODEL_ID) — which Bedrock model to use                    │
# │                                                                             │
# │ deploy.sh injects these into the container via `agentcore deploy --env`.    │
# │ For local development, they come from .env (written by deploy.sh).         │
# │ See gateway_auth.py for how the Cognito token is acquired.                 │
# └─────────────────────────────────────────────────────────────────────────────┘

def _load_env():
    """Load .env from the repo root if environment variables are not already set.

    In the container, deploy.sh injects env vars via `agentcore deploy --env`,
    so this function is a no-op. For local development, it loads from the
    repo-root .env file written by deploy.sh.
    """
    if os.environ.get("AGENTCORE_MCP_URL"):
        return

    # Load from repo root .env (two levels up from src/agentcore/)
    try:
        repo_root = Path(__file__).resolve().parents[2]
        env_path = repo_root / ".env"
        if env_path.exists():
            cfg = dotenv_values(str(env_path))
            for k, v in cfg.items():
                if v and k not in os.environ:
                    os.environ[k] = v
    except Exception as e:
        print(f"[_load_env] Failed to load .env: {e}")

_load_env()

REGION = os.getenv("AWS_REGION", "us-east-1")


def _get_model_id() -> str:
    """Get the configured model ID from environment.

    MODEL_ID is injected into the container by deploy.sh via
    `agentcore deploy --env "MODEL_ID=..."`. For local development,
    it comes from .env (also written by deploy.sh). If neither is set,
    fail fast — the agent should not start with an unknown model.
    """
    model_id = os.getenv("MODEL_ID", "").strip()
    if not model_id:
        raise RuntimeError(
            "MODEL_ID environment variable is not set. "
            "Run 'make deploy' to set it, or add MODEL_ID=<model-id> to .env. "
            "See DEPLOYMENT.md for available model IDs."
        )
    return model_id


# LEARN: BedrockModel wraps the Bedrock InvokeModel API. Temperature 0.0
# makes output deterministic; max_tokens caps cost per invocation.
# Note: Some Claude models do not allow both temperature and top_p to be
# specified simultaneously. We use temperature only (greedy decoding).
_model_cache = None


def _get_model():
    """Create or return the cached BedrockModel instance.

    Lazy initialization avoids calling _get_model_id() at import time,
    which would fail if MODEL_ID isn't set yet (e.g., during test collection).
    """
    global _model_cache
    if _model_cache is None:
        _model_cache = BedrockModel(
            model_id=_get_model_id(),
            region_name=REGION,
            temperature=0.0,
            max_tokens=4000,
        )
    return _model_cache


def _use_hr_tools() -> bool:
    """Check if HR tools should be enabled (default: true)."""
    v = os.environ.get("AGENT_USE_HR_TOOLS", "true").strip().lower()
    return v in ("1", "true", "yes", "on")


def _system_prompt() -> str:
    """Load the system prompt from prompts/onboarding.txt.

    Keeping the prompt in a separate file makes it easier to edit, diff,
    and review without touching Python code.
    """
    prompt_path = Path(__file__).parent / "prompts" / "onboarding.txt"
    return prompt_path.read_text()


# --------------------------------------------------------------------------------------
# App & Telemetry
# --------------------------------------------------------------------------------------

# LEARN: BedrockAgentCoreApp is the runtime framework. It discovers your
# @app.entrypoint handler and serves it as a streaming HTTP endpoint.
app = BedrockAgentCoreApp()


# --------------------------------------------------------------------------------------
# Telemetry
# --------------------------------------------------------------------------------------

_telemetry = StrandsTelemetry()
_telemetry.setup_meter(enable_console_exporter=True)
_telemetry.setup_console_exporter()


# --------------------------------------------------------------------------------------
# MCP Tool Discovery
# --------------------------------------------------------------------------------------
# ┌─────────────────────────────────────────────────────────────────────────────┐
# │ LEARNING CHECKPOINT 2: MCP Tool Discovery                                   │
# │                                                                             │
# │ Instead of hardcoding which tools the agent can use, we discover them       │
# │ at runtime from the AgentCore Gateway via the Model Context Protocol.       │
# │                                                                             │
# │ Flow: Gateway URL → Cognito auth → MCPClient → list_tools_sync()           │
# │                                                                             │
# │ The Gateway knows about tools because deploy.sh registered a Lambda         │
# │ function as an MCP target. The agent just asks "what tools do you have?"    │
# │ and gets back schemas for employee_lookup and it_asset_check.               │
# │                                                                             │
# │ Try: Set AGENT_USE_HR_TOOLS=false in .env and invoke the agent. Compare     │
# │ the output — the model will say it can't retrieve data instead of           │
# │ fabricating answers. This shows the value of tool grounding.                │
# └─────────────────────────────────────────────────────────────────────────────┘

_tools_cache: Optional[List[Any]] = None
_mcp_client = None


def _get_gateway_url() -> Optional[str]:
    """Return the Gateway MCP URL from environment, checking common var names."""
    return (
        os.environ.get("AGENTCORE_MCP_URL")
        or os.environ.get("GATEWAY_URL")
        or None
    )


def _ensure_tools():
    """Discover and return MCP tools from the AgentCore Gateway.

    Uses the Strands MCPClient with streamablehttp transport to connect to the
    Gateway, authenticate via Cognito if configured, and list available tools.
    Results are cached for the lifetime of the process. If you change the
    gateway URL in .env, restart the runtime (or the CLI) to pick up the
    new tools.

    Failure behavior:
    - If AGENT_USE_HR_TOOLS=false, the agent intentionally runs without tools.
      This is useful for teaching comparisons — invoke once with tools, once
      without, observe the difference. Returns [].
    - If tools are expected (the default) but no gateway URL is configured,
      or MCP discovery fails, this function raises. The agent should not
      silently start in a half-configured state.
    """
    global _tools_cache, _mcp_client
    if _tools_cache is not None:
        return _tools_cache

    if not _use_hr_tools():
        print("HR tools disabled via AGENT_USE_HR_TOOLS=false")
        _tools_cache = []
        return _tools_cache

    gateway_url = _get_gateway_url()
    if not gateway_url:
        raise RuntimeError(
            "HR tools are enabled but no gateway URL is configured. "
            "Set AGENTCORE_MCP_URL (or GATEWAY_URL) in .env, or set "
            "AGENT_USE_HR_TOOLS=false to run without tools. "
            "See TROUBLESHOOTING.md for step-by-step diagnosis."
        )

    headers = get_gateway_headers()

    # LEARN: This is MCP tool discovery. The MCPClient connects to the Gateway
    # over streamable HTTP, authenticates with the Cognito token from
    # get_gateway_headers(), and calls list_tools_sync() to learn what tools
    # are available. The agent then knows it can call employee_lookup and
    # it_asset_check — without any hardcoded tool list.
    try:
        from strands.tools.mcp import MCPClient
        from mcp.client.streamable_http import streamablehttp_client

        _mcp_client = MCPClient(
            lambda: streamablehttp_client(gateway_url, headers=headers)
        )
        _mcp_client.__enter__()
        # Ensure the MCP client's HTTP session is closed when the process
        # exits, even though we hold it open for the lifetime of the agent.
        atexit.register(lambda: _mcp_client.__exit__(None, None, None))
        _tools_cache = _mcp_client.list_tools_sync()
        print(f"Discovered {len(_tools_cache)} MCP tools from gateway")
    except Exception as e:
        raise RuntimeError(
            f"MCP tool discovery failed against {gateway_url}: {e}. "
            "Check that the gateway is reachable, Cognito credentials are valid, "
            "and the Lambda MCP target is registered. Set "
            "AGENT_USE_HR_TOOLS=false to run without tools for comparison. "
            "See TROUBLESHOOTING.md for step-by-step diagnosis."
        ) from e

    return _tools_cache


# --------------------------------------------------------------------------------------
# Agent Creation
# --------------------------------------------------------------------------------------
# ┌─────────────────────────────────────────────────────────────────────────────┐
# │ LEARNING CHECKPOINT 3: Assembling the Agent                                 │
# │                                                                             │
# │ A Strands Agent is the combination of four things:                          │
# │   1. A model — Claude Haiku 4.5 via BedrockModel                            │
# │   2. A system prompt — defines behavior, output format, tool-use rules     │
# │   3. Tools — discovered from the MCP Gateway (checkpoint 2)                │
# │   4. A conversation manager — sliding window keeps context bounded         │
# │                                                                             │
# │ The tool-trace hook (attach_tool_trace) captures every tool call so we      │
# │ can show learners exactly what happened in the ToolTrace section.           │
# │ See tool_trace.py for how this works.                                       │
# └─────────────────────────────────────────────────────────────────────────────┘

def _create_agent() -> Agent:
    tools = _ensure_tools()
    # LEARN: This is where the agent comes together. The Strands Agent combines:
    # - A model (Claude Haiku 4.5 via Bedrock)
    # - A system prompt (defines behavior and output format)
    # - Tools (discovered from the MCP Gateway above)
    # - A conversation manager (sliding window keeps context bounded)
    agent = Agent(
        model=_get_model(),
        system_prompt=_system_prompt(),
        tools=tools,
        conversation_manager=SlidingWindowConversationManager(),
    )
    # Install the tool-trace capture hook so we can surface which tools
    # actually ran in the final response (teaching visibility).
    attach_tool_trace(agent)
    return agent


# --------------------------------------------------------------------------------------
# Synchronous invocation (used by CLI REPL)
# --------------------------------------------------------------------------------------
# Streaming entrypoint (AgentCore Runtime)
# --------------------------------------------------------------------------------------
# ┌─────────────────────────────────────────────────────────────────────────────┐
# │ LEARNING CHECKPOINT 4: The AgentCore Streaming Endpoint                     │
# │                                                                             │
# │ This is the function that AgentCore Runtime actually calls. When a client   │
# │ POSTs to the runtime invocation URL:                                        │
# │                                                                             │
# │   Client → HTTPS POST → AgentCore Runtime → endpoint() → SSE stream        │
# │                                                                             │
# │ The @app.entrypoint decorator registers it as the handler. The function     │
# │ yields {"text": ...} dicts that AgentCore streams back as Server-Sent       │
# │ Events. The model's tool calls happen inside agent.stream_async() —         │
# │ Strands handles the tool-call loop automatically.                           │
# │                                                                             │
# │ After streaming completes, we append a ToolTrace block so the client can    │
# │ see which MCP tools ran without checking CloudWatch.                        │
# └─────────────────────────────────────────────────────────────────────────────┘

# LEARN: @app.entrypoint is the decorator that registers this function as
# the AgentCore Runtime's streaming handler. When a client POSTs to the
# runtime invocation URL, AgentCore calls this function and streams the
# yielded {"text": ...} dicts back as Server-Sent Events (SSE).
@app.entrypoint
async def endpoint(payload, context: RequestContext):
    """Streaming entrypoint: yields model output as SSE-compatible text chunks.

    The model's system prompt instructs it to emit tagged blocks
    (Reasoning[tag]/Result[tag]) which downstream consumers (CLI, curl)
    parse directly. After the four onboarding sections finish streaming,
    this entrypoint appends a single `Reasoning[ToolTrace]` / `Result[ToolTrace]`
    block summarizing which MCP tools actually ran so learners can see the
    tool-use loop in action without needing CloudWatch.
    """
    message = (payload or {}).get("message", "").strip()
    if not message:
        yield {"text": "Error: Missing 'message' in payload."}
        return

    agent = _create_agent()

    # Emit model identifier so the learner can verify which model is responding
    yield {"text": f"[Model: {_get_model_id()}]\n\n"}

    # Retry loop for model throttling
    backoff_seconds = [2, 4, 8, 12]
    for idx, delay in enumerate([0] + backoff_seconds):
        try:
            if delay > 0:
                yield {"text": f"Notice: Model rate limited, retrying in {delay}s..."}
                await asyncio.sleep(delay)

            # LEARN: agent.stream_async() is the streaming interface. It yields
            # events as the model generates tokens. We forward text chunks to
            # the caller as SSE data frames. The model's tool calls happen
            # inside this loop — Strands handles them automatically.
            async for event in agent.stream_async(message):
                if isinstance(event, dict):
                    data = event.get("data")
                    if isinstance(data, str) and data:
                        yield {"text": data}
                elif isinstance(event, str) and event:
                    yield {"text": event}

            # After the agent finishes, emit the tool-trace block so learners
            # can see which MCP tools ran (and with what arguments / result
            # summary) inline with the onboarding response.
            captured = getattr(agent, "tool_trace", [])
            yield {"text": format_tool_trace(captured)}

            # Success — exit retry loop
            return

        except ModelThrottledException:
            if idx == len(backoff_seconds):
                yield {"text": "Error: Model request throttled after multiple retries. Please try again shortly."}
                return
            continue
        except Exception as e:
            yield {"text": f"Error: {str(e)}"}
            return


def main():
    app.run()


if __name__ == "__main__":
    main()
