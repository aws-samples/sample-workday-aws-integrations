# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Property-based and unit tests for model ID helper function.

Tests that the _get_model_id() function correctly reads from environment
and provides appropriate defaults.
"""
import os
import sys
from unittest.mock import patch
from hypothesis import given, strategies as st, settings

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'agentcore'))
from onboarding_app import _get_model_id


@given(model_id=st.text(
    min_size=1,
    max_size=200,
    alphabet=st.characters(
        blacklist_categories=('Cc', 'Cs'),
        blacklist_characters='\x00'
    )
).filter(lambda s: s.strip()))
@settings(max_examples=100)
def test_get_model_id_reads_from_environment(model_id):
    """For any value set in MODEL_ID env var, _get_model_id() returns it stripped."""
    with patch.dict(os.environ, {"MODEL_ID": model_id}):
        result = _get_model_id()
        assert result == model_id.strip()


def test_get_model_id_returns_default_when_not_set():
    """When MODEL_ID is not set, raises RuntimeError."""
    import pytest
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(RuntimeError, match="MODEL_ID environment variable is not set"):
            _get_model_id()


def test_get_model_id_with_empty_string():
    """When MODEL_ID is explicitly empty, raises RuntimeError."""
    import pytest
    with patch.dict(os.environ, {"MODEL_ID": ""}):
        with pytest.raises(RuntimeError, match="MODEL_ID environment variable is not set"):
            _get_model_id()


def test_get_model_id_with_special_characters():
    """Model IDs with colons, periods, and hyphens are handled correctly."""
    test_cases = [
        "anthropic.claude-3-5-sonnet-20240620-v1:0",
        "anthropic.claude-3-haiku-20240307-v1:0",
        "amazon.titan-text-premier-v1:0",
        "anthropic.claude-3-7-sonnet-20250219-v1:0",
    ]
    for model_id in test_cases:
        with patch.dict(os.environ, {"MODEL_ID": model_id}):
            result = _get_model_id()
            assert result == model_id
