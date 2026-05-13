# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Tests for src/agentcore/tool_trace.py

Example-based tests verify specific summarization and formatting scenarios.
Property-based tests verify return-type and structural invariants.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "agentcore"))

from tool_trace import summarize_tool_result, format_tool_trace

from hypothesis import given, settings, strategies as st


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

@st.composite
def tool_result_dicts(draw):
    """Generate dicts mimicking Strands ToolResult shape."""
    status = draw(st.sampled_from(["success", "error", "unknown"]))
    content_type = draw(st.sampled_from(["text", "json", "empty"]))

    if content_type == "text":
        text_val = draw(st.text(min_size=0, max_size=200))
        content = [{"text": text_val}]
    elif content_type == "json":
        json_val = draw(st.one_of(
            st.dictionaries(st.text(min_size=1, max_size=10), st.integers(), max_size=5),
            st.just({"results_count": draw(st.integers(min_value=0, max_value=100))}),
        ))
        content = [{"json": json_val}]
    else:
        content = []

    return {"status": status, "content": content}


def any_value():
    """Strategy producing arbitrary Python values for summarize_tool_result."""
    return st.one_of(
        st.none(),
        st.integers(),
        st.text(max_size=50),
        st.lists(st.integers(), max_size=5),
        tool_result_dicts(),
    )


@st.composite
def captured_entries(draw):
    """Generate lists of captured tool call entries."""
    n = draw(st.integers(min_value=1, max_value=5))
    entries = []
    for _ in range(n):
        entries.append({
            "name": draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("L", "N")))),
            "input": draw(st.dictionaries(st.text(min_size=1, max_size=10), st.text(max_size=20), max_size=3)),
            "summary": draw(st.text(max_size=50)),
        })
    return entries


# ===========================================================================
# Example-based tests (Task 3.1)
# ===========================================================================


def test_non_dict_returns_no_result():
    """Non-dict values return 'no result'."""
    assert summarize_tool_result(None) == "no result"
    assert summarize_tool_result(42) == "no result"
    assert summarize_tool_result("hello") == "no result"


def test_error_status_returns_error_prefix():
    """Error status with text content returns 'error: ...'."""
    result = {"status": "error", "content": [{"text": "something broke"}]}
    summary = summarize_tool_result(result)
    assert summary.startswith("error:")


def test_results_count_key():
    """JSON content with results_count returns 'N item(s) returned'."""
    result = {"status": "success", "content": [{"json": {"results_count": 5}}]}
    summary = summarize_tool_result(result)
    assert "item(s) returned" in summary


def test_dict_without_count_keys():
    """JSON dict without count keys returns 'object with keys: ...'."""
    result = {"status": "success", "content": [{"json": {"foo": 1, "bar": 2}}]}
    summary = summarize_tool_result(result)
    assert summary.startswith("object with keys:")


def test_text_content_returned():
    """Text content is returned directly; long text is truncated."""
    short = {"status": "success", "content": [{"text": "short text"}]}
    assert summarize_tool_result(short) == "short text"

    long_text = "x" * 200
    long_result = {"status": "success", "content": [{"text": long_text}]}
    summary = summarize_tool_result(long_result)
    assert len(summary) <= 123  # 120 + "..."
    assert summary.endswith("...")


def test_empty_content_list():
    """Empty content list returns 'empty result'."""
    result = {"status": "success", "content": []}
    assert summarize_tool_result(result) == "empty result"


def test_format_empty_list():
    """Empty captured list mentions no tools were called."""
    output = format_tool_trace([])
    assert "No MCP tools were called" in output
    assert "ToolTrace" in output


def test_format_with_entries():
    """Non-empty captured list has ToolTrace tag and one bullet per entry."""
    entries = [
        {"name": "employee_lookup", "input": {"query": "engineering"}, "summary": "3 item(s) returned"},
        {"name": "it_asset_check", "input": {"action": "get_recommendations"}, "summary": "object with keys: laptop, monitor"},
    ]
    output = format_tool_trace(entries)
    assert "ToolTrace" in output
    bullet_lines = [line for line in output.splitlines() if line.strip().startswith("- ")]
    assert len(bullet_lines) == 2


# ===========================================================================
# Property-based tests (Task 3.2)
# ===========================================================================


@given(val=any_value())
@settings(max_examples=100)
def test_prop_summarize_always_returns_str(val):
    """Property 4: summarize_tool_result always returns a string.

    Feature: expand-test-coverage, Property 4: summarize_tool_result always returns a string
    """
    assert isinstance(summarize_tool_result(val), str)


@given(entries=captured_entries())
@settings(max_examples=100)
def test_prop_format_contains_tooltrace_tag(entries):
    """Property 5: format_tool_trace output always contains ToolTrace tag.

    Feature: expand-test-coverage, Property 5: format_tool_trace output always contains ToolTrace tag
    """
    output = format_tool_trace(entries)
    assert "ToolTrace" in output


@given(entries=captured_entries())
@settings(max_examples=100)
def test_prop_format_bullet_count_matches(entries):
    """Property 6: format_tool_trace bullet count matches entry count.

    Feature: expand-test-coverage, Property 6: format_tool_trace bullet count matches entry count
    """
    output = format_tool_trace(entries)
    bullet_lines = [line for line in output.splitlines() if line.strip().startswith("- ")]
    assert len(bullet_lines) == len(entries)
