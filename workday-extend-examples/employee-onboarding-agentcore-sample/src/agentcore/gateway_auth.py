# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Cognito OAuth2 helper for authenticating MCP calls to the AgentCore Gateway.

This module handles the client-credentials token flow that the agent uses to
authenticate its MCP tool-discovery and tool-invocation requests. The token
is fetched directly via urllib3 (a transitive dependency of boto3, always
available in the container) rather than importing the host-side starter toolkit.

Learners: this is the same OAuth2 client-credentials flow that the CLI uses
to authenticate to the Runtime — but here the *agent itself* is the client,
authenticating to the *Gateway* so it can call MCP tools.
"""

import base64
import json
import os
import urllib.parse
from typing import Dict


def get_gateway_headers() -> Dict[str, str]:
    """Build HTTP headers for MCP calls to the AgentCore Gateway.

    When Cognito OAuth2 is configured (all four required COGNITO_* env vars
    are set: client_id, client_secret, token_endpoint, scope), fetches a
    client-credentials token and returns headers with a Bearer token.

    When the Cognito env vars are missing, returns plain headers with no
    Authorization. The MCP request will reach the gateway as an anonymous
    call; whether it succeeds depends on how the gateway was configured.

    If Cognito is configured but the token call fails, raises RuntimeError.
    """
    client_info = {
        "client_id": os.environ.get("COGNITO_CLIENT_ID", ""),
        "client_secret": os.environ.get("COGNITO_CLIENT_SECRET", ""),
        "token_endpoint": os.environ.get("COGNITO_TOKEN_ENDPOINT", ""),
        "scope": os.environ.get("COGNITO_SCOPE", ""),
    }

    headers = {"Content-Type": "application/json"}

    if not all(client_info.values()):
        # Not all required Cognito fields present. Proceed without auth.
        return headers

    # Fetch a client-credentials token directly via urllib3 (available in
    # every Python environment that has boto3). Uses HTTP Basic Auth per
    # RFC 6749 §2.3.1, matching the pattern in onboarding_cli.py.
    import urllib3

    basic_credentials = base64.b64encode(
        f"{client_info['client_id']}:{client_info['client_secret']}".encode()
    ).decode()
    form_data = {
        "grant_type": "client_credentials",
        "scope": client_info["scope"],
    }
    http = urllib3.PoolManager()
    resp = http.request(
        "POST",
        client_info["token_endpoint"],
        body=urllib.parse.urlencode(form_data),
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {basic_credentials}",
        },
        timeout=10.0,
        retries=False,
    )
    if resp.status != 200:
        raise RuntimeError(
            f"Cognito token request failed (HTTP {resp.status}): "
            f"{resp.data.decode()}"
        )
    token_data = json.loads(resp.data.decode())
    headers["Authorization"] = f"Bearer {token_data['access_token']}"
    return headers
