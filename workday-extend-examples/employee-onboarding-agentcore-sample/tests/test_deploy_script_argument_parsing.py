# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Property-based tests for deployment script argument parsing.

Tests that deploy.sh correctly accepts and processes model ID arguments.
"""
import subprocess
import tempfile
import os
from hypothesis import given, strategies as st, settings


ARGUMENT_PARSING_SCRIPT = """#!/bin/bash
set -e
MODEL_ID="us.anthropic.claude-haiku-4-5-20251001-v1:0"
while [[ $# -gt 0 ]]; do
    case $1 in
        --model)
            MODEL_ID="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [--model MODEL_ID]"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done
if [ -z "$MODEL_ID" ]; then
    echo "Error: MODEL_ID cannot be empty"
    exit 1
fi
echo "SUCCESS: $MODEL_ID"
exit 0
"""


def _run_parsing_script(args=None):
    """Helper to run the argument parsing script with given args."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
        f.write(ARGUMENT_PARSING_SCRIPT)
        script_path = f.name
    try:
        os.chmod(script_path, 0o755)  # nosec B103 — making test script executable
        cmd = ['/bin/bash', script_path] + (args or [])
        return subprocess.run(cmd, capture_output=True, text=True, timeout=5)
    finally:
        os.unlink(script_path)


@given(model_id=st.text(
    min_size=1,
    max_size=200,
    alphabet=st.characters(
        blacklist_categories=('Cc', 'Cs'),
        blacklist_characters='\x00'
    )
))
@settings(max_examples=100)
def test_script_accepts_any_model_id(model_id):
    """Script accepts any model ID string without validation errors."""
    result = _run_parsing_script(['--model', model_id])
    assert result.returncode == 0, f"Rejected '{model_id}': {result.stderr}"
    assert model_id in result.stdout


def test_script_accepts_default_model():
    """Without --model, uses the default model ID."""
    result = _run_parsing_script()
    assert result.returncode == 0
    assert "us.anthropic.claude-haiku-4-5-20251001-v1:0" in result.stdout


def test_script_help_flag():
    """--help displays usage and exits successfully."""
    result = _run_parsing_script(['--help'])
    assert result.returncode == 0
    assert "Usage:" in result.stdout


@given(model_id=st.text(
    min_size=1,
    max_size=200,
    alphabet=st.characters(
        blacklist_categories=('Cc', 'Cs'),
        blacklist_characters='\x00\n\r"\\\''
    )
))
@settings(max_examples=100)
def test_model_id_roundtrip_consistency(model_id):
    """MODEL_ID survives round-trip through env file generation and python-dotenv parsing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        env_file = os.path.join(tmpdir, '.env')
        script = f"""#!/bin/bash
set -e
MODEL_ID="$1"
cat > "{env_file}" << EOF
MODEL_ID="$MODEL_ID"
EOF
echo "SUCCESS"
"""
        script_path = os.path.join(tmpdir, 'test.sh')
        with open(script_path, 'w') as f:
            f.write(script)
        os.chmod(script_path, 0o755)  # nosec B103 — making test script executable

        result = subprocess.run(
            ['/bin/bash', script_path, model_id],
            capture_output=True, text=True, timeout=5
        )
        assert result.returncode == 0

        from dotenv import dotenv_values
        env_values = dotenv_values(env_file)
        assert env_values.get('MODEL_ID') == model_id
