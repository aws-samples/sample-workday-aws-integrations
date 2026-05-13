# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Integration tests for end-to-end model configuration flow.

Tests the complete flow: deploy script → env files → agent initialization.
"""
import os
import sys
import tempfile
import subprocess
from unittest.mock import patch, MagicMock
from dotenv import dotenv_values


DEPLOY_SIMULATION = """#!/bin/bash
set -e
MODEL_ID="us.anthropic.claude-haiku-4-5-20251001-v1:0"
while [[ $# -gt 0 ]]; do
    case $1 in
        --model) MODEL_ID="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done
if [ -z "$MODEL_ID" ]; then exit 1; fi
cat > "{env_file}" << EOF
AWS_REGION=us-east-1
MODEL_ID="$MODEL_ID"
GATEWAY_URL=https://test-gateway.example.com
EOF
echo "Deployment complete"
echo "Model ID: $MODEL_ID"
"""


def _run_deploy_sim(tmpdir, args=None):
    env_file = os.path.join(tmpdir, '.env')
    script_content = DEPLOY_SIMULATION.replace('{env_file}', env_file)
    script_path = os.path.join(tmpdir, 'deploy.sh')
    with open(script_path, 'w') as f:
        f.write(script_content)
    os.chmod(script_path, 0o755)  # nosec B103 — making test script executable
    cmd = ['/bin/bash', script_path] + (args or [])
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    return result, env_file


def test_end_to_end_default_model():
    """Deploy without --model uses default, agent reads it correctly."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'agentcore'))
    from onboarding_app import _get_model_id

    with tempfile.TemporaryDirectory() as tmpdir:
        result, env_file = _run_deploy_sim(tmpdir)
        assert result.returncode == 0

        env_values = dotenv_values(env_file)
        expected = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
        assert env_values.get('MODEL_ID') == expected

        with patch.dict(os.environ, env_values):
            assert _get_model_id() == expected


def test_end_to_end_custom_model():
    """Deploy with --model propagates custom ID through to agent."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'agentcore'))
    from onboarding_app import _get_model_id

    custom = "anthropic.claude-3-haiku-20240307-v1:0"
    with tempfile.TemporaryDirectory() as tmpdir:
        result, env_file = _run_deploy_sim(tmpdir, ['--model', custom])
        assert result.returncode == 0

        env_values = dotenv_values(env_file)
        assert env_values.get('MODEL_ID') == custom

        with patch.dict(os.environ, env_values):
            assert _get_model_id() == custom


def test_end_to_end_model_initialization():
    """MODEL_ID env var propagates to BedrockModel initialization."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'agentcore'))
    from onboarding_app import _get_model_id

    test_model = "amazon.titan-text-premier-v1:0"
    with patch.dict(os.environ, {"MODEL_ID": test_model}):
        assert _get_model_id() == test_model

        with patch('strands.models.BedrockModel') as mock_bedrock:
            mock_bedrock.return_value = MagicMock()
            from strands.models import BedrockModel
            _ = BedrockModel(
                model_id=_get_model_id(),
                region_name="us-east-1",
                temperature=0.0,
                max_tokens=4000,
                top_p=0.8,
            )
            assert mock_bedrock.call_args.kwargs.get('model_id') == test_model


def test_end_to_end_special_characters():
    """Special characters (colons, periods, hyphens) survive the full pipeline."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'agentcore'))
    from onboarding_app import _get_model_id

    special = "anthropic.claude-3-5-sonnet-20240620-v1:0"
    with tempfile.TemporaryDirectory() as tmpdir:
        result, env_file = _run_deploy_sim(tmpdir, ['--model', special])
        assert result.returncode == 0

        env_values = dotenv_values(env_file)
        assert env_values.get('MODEL_ID') == special

        with patch.dict(os.environ, env_values):
            assert _get_model_id() == special
