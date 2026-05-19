# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Lambda function that serves as MCP server for HR tools.

Handles two invocation formats:
1. MCP JSON-RPC format: {"method": "tools/list"|"tools/call", "params": {...}}
   Used during MCP tool discovery (list_tools_sync).
2. Gateway direct format: {"query": "...", "find_manager": true, ...}
   Used when the AgentCore Gateway invokes a specific tool — the gateway
   sends only the tool's input arguments as the top-level event dict.
   We infer which tool to call from the argument keys.
"""
import json
import logging
from tools.hr_tools import HR_TOOLS

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Map distinctive required keys to tool names for gateway direct invocations.
# When the Gateway calls the Lambda directly (not via MCP JSON-RPC), it sends
# only the tool's input arguments as the event dict. We infer which tool to
# call by looking for a key unique to that tool's schema.
#
# Limitation: if you add a new tool that also has a "query" or "action"
# parameter, add a different distinctive key here to avoid collisions.
_TOOL_ROUTING = {
    "query": "employee_lookup",      # employee_lookup requires "query"
    "action": "it_asset_check",      # it_asset_check requires "action"
}


def lambda_handler(event, context):
    """Handle MCP requests for HR tools."""
    try:
        method = event.get("method", "")

        # ── MCP JSON-RPC format (used by MCP client discovery) ──
        if method == "tools/list":
            tools = [tc.get_schema() for tc in HR_TOOLS.values()]
            return {
                "statusCode": 200,
                "body": json.dumps({"tools": tools}),
            }

        if method == "tools/call":
            params = event.get("params", {})
            return _call_tool(params.get("name", ""), params.get("arguments", {}))

        # ── Gateway direct format (just the tool arguments) ──
        if not method and isinstance(event, dict):
            for key, tool_name in _TOOL_ROUTING.items():
                if key in event:
                    return _call_tool(tool_name, event)
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": f"Cannot determine tool from arguments: {list(event.keys())}"
                }),
            }

        return {
            "statusCode": 400,
            "body": json.dumps({"error": f"Unknown method: {method}"}),
        }

    except Exception as e:
        # Log the full error for CloudWatch debugging; return a generic
        # message to avoid leaking internal details through tool responses.
        logger.exception("Unhandled error in lambda_handler")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal tool error"}),
        }


def _call_tool(tool_name, arguments):
    """Execute a tool by name with the given arguments."""
    if tool_name not in HR_TOOLS:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": f"Unknown tool: {tool_name}"}),
        }
    tool_class = HR_TOOLS[tool_name]
    result = tool_class.execute(**arguments)
    return {
        "statusCode": 200,
        "body": json.dumps({
            "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
        }),
    }
