# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Tool-call tracing for teaching visibility.

After the agent finishes, the response includes a ToolTrace section that shows
learners exactly which MCP tools were called, with what arguments, and a short
summary of what each tool returned. This module handles capturing those calls
(via a Strands AfterToolCallEvent hook) and formatting them into the tagged
text block that the response parser and UI expect.

Learners: this is how you can observe the agent's tool-use loop without
digging through CloudWatch logs. The ToolTrace section appears at the end
of every response, right after the four onboarding sections.
"""

from typing import Any, Dict, List

_TOOL_TRACE_TAG = "ToolTrace"


def summarize_tool_result(tool_result: Any) -> str:
    """Produce a short, human-readable summary of a Strands ToolResult.

    Keeps the trailing ToolTrace block readable rather than dumping raw JSON.
    """
    if not isinstance(tool_result, dict):
        return "no result"

    status = tool_result.get("status", "unknown")
    if status == "error":
        for item in tool_result.get("content", []) or []:
            if isinstance(item, dict) and "text" in item:
                return f"error: {str(item['text'])[:120]}"
        return "error"

    # Success path — collapse content items to a tiny preview.
    for item in tool_result.get("content", []) or []:
        if not isinstance(item, dict):
            continue
        if "json" in item:
            value = item["json"]
            if isinstance(value, dict):
                for count_key in ("results_count", "total_items", "count"):
                    if count_key in value:
                        return f"{value[count_key]} item(s) returned"
                keys = ", ".join(list(value.keys())[:4])
                return f"object with keys: {keys}"
            return "structured data returned"
        if "text" in item:
            text = str(item["text"]).replace("\n", " ").strip()
            return (text[:120] + "...") if len(text) > 120 else text

    return "empty result"


def format_tool_trace(captured: List[Dict[str, Any]]) -> str:
    """Render captured tool calls as a Reasoning[ToolTrace] + Result[ToolTrace] block.

    The response parser's allowlist includes 'tooltrace' so this block is
    picked up as a fifth section alongside the four onboarding sections.
    """
    if not captured:
        return (
            f"\nReasoning[{_TOOL_TRACE_TAG}]: No MCP tools were called during this invocation."
            f"\nResult[{_TOOL_TRACE_TAG}]: The agent produced its response without consulting any tools.\n"
        )

    bullets = []
    for entry in captured:
        name = entry.get("name", "unknown")
        raw_input = entry.get("input") or {}
        if isinstance(raw_input, dict):
            compact = {
                k: (v if len(str(v)) <= 80 else f"{str(v)[:77]}...")
                for k, v in raw_input.items()
            }
            input_str = ", ".join(f"{k}={v!r}" for k, v in compact.items())
        else:
            input_str = str(raw_input)[:120]
        summary = entry.get("summary", "")
        bullets.append(f"- {name}({input_str}) -> {summary}")

    lines = [
        f"Reasoning[{_TOOL_TRACE_TAG}]: The following MCP tools were invoked while building this response.",
        f"Result[{_TOOL_TRACE_TAG}]:",
    ] + bullets
    return "\n" + "\n".join(lines) + "\n"


def attach_tool_trace(agent: "Any") -> List[Dict[str, Any]]:
    """Register an AfterToolCallEvent hook on ``agent`` that captures tool calls.

    Returns the list that the hook appends to. Also attached to the agent
    as ``agent.tool_trace`` for convenience.
    """
    from strands.hooks import AfterToolCallEvent

    captured: List[Dict[str, Any]] = []

    def _on_after_tool_call(event: "AfterToolCallEvent") -> None:
        tool_use = event.tool_use or {}
        captured.append(
            {
                "name": tool_use.get("name", "unknown"),
                "input": tool_use.get("input", {}),
                "summary": summarize_tool_result(event.result),
            }
        )

    agent.hooks.add_callback(AfterToolCallEvent, _on_after_tool_call)
    agent.tool_trace = captured  # type: ignore[attr-defined]
    return captured
