# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""CLI entrypoint for the HR onboarding agent.

Collects the full streamed response from the AgentCore runtime, parses it
into sections, and prints a clean, human-readable onboarding package.
Use --debug to also see the raw SSE transcript.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import time
import uuid
import urllib.parse
from pathlib import Path
from typing import Dict, List, Optional

import requests
import yaml
from dotenv import dotenv_values

# Allow running via `python src/cli/onboarding_cli.py` from the repo root
# without installing the repo as a package. We add src/agentcore/ to the path
# so response_parser can be imported directly (same pattern onboarding_app.py uses).
_AGENTCORE_DIR = str(Path(__file__).resolve().parents[1] / "agentcore")
if _AGENTCORE_DIR not in sys.path:
    sys.path.insert(0, _AGENTCORE_DIR)

from response_parser import collapse_sections, parse_sectioned_transcript

SECTION_ORDER = ("it", "welcome", "daily", "first30", "tooltrace")
SECTION_TITLES = {
    "it": "IT Provisioning",
    "welcome": "Welcome Email",
    "daily": "Daily Activities",
    "first30": "First 30 Days",
    "tooltrace": "MCP Tools Used",
}


def load_env() -> None:
    """Load environment variables from .env if present."""
    env_path = Path(".env")
    if env_path.exists():
        cfg = dotenv_values(str(env_path))
        for key, value in cfg.items():
            if value and key not in os.environ:
                os.environ[key] = value


def get_runtime_config() -> tuple[str, str]:
    """Read runtime configuration produced by deployment scripts."""
    config_path = Path(".bedrock_agentcore.yaml")
    if not config_path.exists():
        print("Error: .bedrock_agentcore.yaml not found. Please run 'make deploy' first.")
        raise SystemExit(1)
    cfg = yaml.safe_load(config_path.read_text())
    agent_cfg = cfg["agents"][cfg["default_agent"]]
    region = agent_cfg["aws"]["region"] or os.environ.get("AWS_REGION", "us-east-1")
    agent_arn = agent_cfg["bedrock_agentcore"]["agent_arn"]
    return region, agent_arn


def get_user_token() -> str:
    """Exchange client credentials for an OAuth2 token."""
    cid = os.environ["RUNTIME_CLIENT_ID"]
    csec = os.environ["RUNTIME_CLIENT_SECRET"]
    token_endpoint = os.environ["RUNTIME_TOKEN_ENDPOINT"]
    scope = os.environ["RUNTIME_SCOPE"]
    basic = base64.b64encode(f"{cid}:{csec}".encode()).decode()
    headers = {"Authorization": f"Basic {basic}", "Content-Type": "application/x-www-form-urlencoded"}
    data = {"grant_type": "client_credentials", "scope": scope}
    response = requests.post(token_endpoint, headers=headers, data=data, timeout=30)
    response.raise_for_status()
    return response.json().get("access_token", "")


def collect_transcript(url: str, headers: Dict[str, str], message: str) -> str:
    """POST to the runtime and concatenate all streamed SSE text into one string.

    Prints a simple progress indicator to stderr so the user sees the run is
    alive, without cluttering stdout (which stays reserved for the formatted
    onboarding package).
    """
    parts: List[str] = []
    last_tick = time.monotonic()
    chunk_count = 0

    # 900s accommodates the longest observed agent runs (~3-5 min for complex
    # onboarding packages with model-throttle retries). Reduce for tighter
    # feedback loops in your own agents.
    with requests.post(url, headers=headers, json={"message": message}, timeout=900, stream=True) as resp:
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")

        # Non-streaming response: runtime returned JSON/text in one shot.
        if "text/event-stream" not in content_type:
            if content_type.startswith("application/json"):
                return json.dumps(resp.json())
            return resp.text

        for raw in resp.iter_lines(chunk_size=1):
            if not raw:
                continue
            line = raw.decode("utf-8", "ignore")
            if not line.startswith("data: "):
                continue
            payload = line[6:]
            try:
                obj = json.loads(payload)
                if isinstance(obj, dict) and isinstance(obj.get("text"), str):
                    text = obj["text"]
                elif isinstance(obj, str):
                    text = obj
                else:
                    text = payload
            except Exception:
                text = payload

            if not text:
                continue
            parts.append(text)
            chunk_count += 1

            # Emit a dot on stderr every ~1s so users see progress.
            now = time.monotonic()
            if now - last_tick >= 1.0:
                sys.stderr.write(".")
                sys.stderr.flush()
                last_tick = now

    if chunk_count:
        sys.stderr.write("\n")
        sys.stderr.flush()

    return "".join(parts)


def print_divider(title: str) -> None:
    """Render a bold, underlined section header."""
    bar = "━" * max(len(title), 40)
    print(f"\n{bar}")
    print(title.upper())
    print(bar)


def render_package(sections: Dict[str, Dict[str, str]]) -> bool:
    """Print the four onboarding sections in a consistent layout.

    Returns True if anything was rendered, False if all sections were empty.
    """
    rendered = False
    for tag in SECTION_ORDER:
        section = sections.get(tag, {})
        result = (section.get("result") or "").strip()
        reasoning = (section.get("reasoning") or "").strip()
        if not result and not reasoning:
            continue

        print_divider(SECTION_TITLES[tag])

        if result:
            print(result)
            rendered = True
        elif reasoning:
            # Only show reasoning if the model didn't produce a result block.
            print(f"(reasoning only)\n{reasoning}")
            rendered = True
    return rendered


def run(message: str, debug: bool = False) -> int:
    """Top-level entry: invoke the runtime, parse, render."""
    load_env()
    region, agent_arn = get_runtime_config()
    token = get_user_token()

    session_id = str(uuid.uuid4())
    encoded_arn = urllib.parse.quote(agent_arn, safe="")
    url = (
        f"https://bedrock-agentcore.{region}.amazonaws.com/"
        f"runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": session_id,
    }

    print(f"Employee Onboarding")
    print(f"Session: {session_id}")
    print(f"Logs:    CloudWatch → /aws/bedrock-agentcore/runtimes/")
    sys.stderr.write("Generating onboarding package")
    sys.stderr.flush()

    transcript = collect_transcript(url, headers, message)

    # Extract and display the model identifier emitted by the runtime
    model_match = re.search(r"\[Model:\s*([^\]]+)\]", transcript)
    if model_match:
        print(f"Model:   {model_match.group(1).strip()}")

    sections = collapse_sections(parse_sectioned_transcript(transcript))

    rendered = render_package(sections)

    if not rendered:
        print("\nThe agent returned no structured content.")
        if transcript.strip():
            print("\nRaw response (truncated):")
            snippet = transcript if len(transcript) < 2000 else transcript[:2000] + "\n..."
            print(snippet)
        else:
            print("No content returned from the runtime.")
        return 1

    if debug:
        print_divider("Raw SSE Transcript (debug)")
        print(transcript if transcript else "<no content>")

    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Call the HR onboarding agent and print a formatted onboarding package.",
    )
    parser.add_argument(
        "prompt",
        help="User instruction to send to the onboarding agent.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Also print the raw SSE transcript after the formatted view.",
    )
    args = parser.parse_args(argv)
    return run(args.prompt, debug=args.debug)


if __name__ == "__main__":
    raise SystemExit(main())
