# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Tests for src/agentcore/response_parser.py

Example-based tests verify specific parsing scenarios.
Property-based tests verify structural invariants across arbitrary inputs.
"""

import os
import sys

# Follow existing project convention for importing src/agentcore modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "agentcore"))

from response_parser import (
    SECTION_NAMES,
    parse_sectioned_transcript,
    collapse_sections,
)

from hypothesis import given, settings, strategies as st


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

@st.composite
def tagged_transcript(draw):
    """Generate multi-line strings with valid Label[section]: body lines,
    optional untagged continuations, and blank lines."""
    sections = st.sampled_from(list(SECTION_NAMES))
    labels = st.sampled_from(["Reasoning", "Result", "Tool"])
    body_text = st.text(
        alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z"), blacklist_characters="\n\r"),
        min_size=1,
        max_size=40,
    )

    num_lines = draw(st.integers(min_value=0, max_value=10))
    lines = []
    for _ in range(num_lines):
        section = draw(sections)
        label = draw(labels)
        body = draw(body_text)
        lines.append(f"{label}[{section}]: {body}")

        # Optionally add untagged continuation lines
        num_continuations = draw(st.integers(min_value=0, max_value=2))
        for _ in range(num_continuations):
            continuation = draw(body_text)
            lines.append(continuation)

        # Optionally add a blank line
        if draw(st.booleans()):
            lines.append("")

    return "\n".join(lines)


# ===========================================================================
# Example-based tests (Task 1.1)
# ===========================================================================


def test_all_five_sections_present():
    """Parse a transcript with all five section tags; dict has exactly SECTION_NAMES keys."""
    transcript = (
        "Reasoning[it]: thinking about IT\n"
        "Result[welcome]: welcome message\n"
        "Tool[daily]: daily tool note\n"
        "Reasoning[first30]: first 30 days reasoning\n"
        "Result[tooltrace]: tooltrace result\n"
    )
    sections = parse_sectioned_transcript(transcript)
    assert set(sections.keys()) == set(SECTION_NAMES)


def test_reasoning_tag_placement():
    """Reasoning[it]: some text -> sections['it']['reasoning'] contains 'some text'."""
    sections = parse_sectioned_transcript("Reasoning[it]: some text")
    assert "some text" in sections["it"]["reasoning"]


def test_result_tag_placement():
    """Result[welcome]: some text -> sections['welcome']['result'] contains 'some text'."""
    sections = parse_sectioned_transcript("Result[welcome]: some text")
    assert "some text" in sections["welcome"]["result"]


def test_untagged_continuation():
    """Untagged line following a tagged line is appended to current section/label."""
    transcript = "Reasoning[it]: first line\nsecond line continues"
    sections = parse_sectioned_transcript(transcript)
    assert "first line" in sections["it"]["reasoning"]
    assert "second line continues" in sections["it"]["reasoning"]


def test_empty_input():
    """Empty string produces empty lists for all sections."""
    sections = parse_sectioned_transcript("")
    for name in SECTION_NAMES:
        assert sections[name]["reasoning"] == []
        assert sections[name]["result"] == []
        assert sections[name]["tools"] == []


def test_collapse_joins_fragments():
    """Multiple fragments per label are joined with newlines."""
    parsed = {
        name: {"reasoning": ["line1", "line2"], "result": ["a"], "tools": []}
        for name in SECTION_NAMES
    }
    collapsed = collapse_sections(parsed)
    for name in SECTION_NAMES:
        assert collapsed[name]["reasoning"] == "line1\nline2"
        assert collapsed[name]["result"] == "a"


def test_collapse_empty_fragments():
    """Empty fragment lists become empty strings."""
    parsed = {
        name: {"reasoning": [], "result": [], "tools": []}
        for name in SECTION_NAMES
    }
    collapsed = collapse_sections(parsed)
    for name in SECTION_NAMES:
        assert collapsed[name]["reasoning"] == ""
        assert collapsed[name]["result"] == ""
        assert collapsed[name]["tools"] == ""


# ===========================================================================
# Property-based tests (Task 1.2)
# ===========================================================================


@given(text=tagged_transcript())
@settings(max_examples=100)
def test_prop_key_set_invariant(text):
    """Property 1: Parsed output key set equals SECTION_NAMES.

    **Validates: Requirements 2.1**

    Feature: expand-test-coverage, Property 1: Parsed output key set equals SECTION_NAMES
    """
    sections = parse_sectioned_transcript(text)
    assert set(sections.keys()) == set(SECTION_NAMES)


@given(text=tagged_transcript())
@settings(max_examples=100)
def test_prop_inner_key_set_invariant(text):
    """Property 2: Each parsed section has exactly reasoning/result/tools keys.

    **Validates: Requirement 2.2**

    Feature: expand-test-coverage, Property 2: Each parsed section has exactly reasoning/result/tools keys
    """
    sections = parse_sectioned_transcript(text)
    expected_keys = {"reasoning", "result", "tools"}
    for section_name, section_data in sections.items():
        assert set(section_data.keys()) == expected_keys
        for key in expected_keys:
            assert isinstance(section_data[key], list)


@given(text=tagged_transcript())
@settings(max_examples=100)
def test_prop_collapse_produces_strings(text):
    """Property 3: Parse-then-collapse pipeline produces string leaves.

    **Validates: Requirements 2.3, 2.4**

    Feature: expand-test-coverage, Property 3: Parse-then-collapse pipeline produces string leaves
    """
    parsed = parse_sectioned_transcript(text)
    collapsed = collapse_sections(parsed)
    for section_name, section_data in collapsed.items():
        for key, value in section_data.items():
            assert isinstance(value, str)
