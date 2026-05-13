# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Helpers for parsing section-tagged onboarding responses.

This is the canonical (and only) copy of the parser. It lives in
src/agentcore/ so it ships inside the AgentCore Runtime container via
direct_code_deploy. The CLI imports it from here too.
"""

from __future__ import annotations

import re
from typing import Dict, List

SECTION_NAMES = ("it", "welcome", "daily", "first30", "tooltrace")
# The model usually emits "Reasoning[section]:" and "Result[section]:" labels,
# but occasionally uses synonyms like "Think" or "Final". This map normalizes
# all variants to the three canonical keys: reasoning, result, tools.
LABEL_NORMALIZATION = {
    "reasoning": "reasoning",
    "think": "reasoning",
    "thought": "reasoning",
    "result": "result",
    "final": "result",
    "tool": "tools",
}

TAG_PATTERN = re.compile(
    r"^(?P<label>\w+)\[\s*(?P<section>it|welcome|daily|first30|tooltrace)\s*\]\s*:\s*(?P<body>.*)$",
    re.IGNORECASE,
)
# Matches strings like "Reasoning[it]: ..." or "Tool[daily]: ..."


def parse_sectioned_transcript(text: str) -> Dict[str, Dict[str, List[str]]]:
    """Parse tagged transcript text into per-section buckets.

    Returns a dict keyed by section tag (it|welcome|daily|first30) with subkeys:
      - reasoning: list of reasoning snippets
      - result: list of final narrative snippets
      - tools: list of tool usage notes
    Untagged lines are appended to the most recently seen section/label.
    """

    sections: Dict[str, Dict[str, List[str]]] = {
        key: {"reasoning": [], "result": [], "tools": []} for key in SECTION_NAMES
    }
    current_section: str | None = None
    current_label: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        match = TAG_PATTERN.match(line)
        if match:
            current_section = match.group("section").lower()
            label = match.group("label").lower()
            current_label = LABEL_NORMALIZATION.get(label)
            body = match.group("body").strip()
            if current_label and current_section in sections and body:
                sections[current_section][current_label].append(body)
            continue

        if current_section and current_label and current_section in sections:
            sections[current_section][current_label].append(line)

    return sections


def collapse_sections(parsed: Dict[str, Dict[str, List[str]]]) -> Dict[str, Dict[str, str]]:
    """Collapse list-based parser output into single strings per field.

    The model sometimes emits multiple lines per label. Joining them here keeps
    downstream consumers simple: they can treat each field as a single string.
    """
    collapsed: Dict[str, Dict[str, str]] = {}
    for section, buckets in parsed.items():
        collapsed[section] = {}
        for key, fragments in buckets.items():
            text = "\n".join(fragment for fragment in fragments if fragment is not None).strip()
            collapsed[section][key] = text
    return collapsed
