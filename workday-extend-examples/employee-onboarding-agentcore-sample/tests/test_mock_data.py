# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Tests for tools/mock_data.py

Example-based tests verify specific search and recommendation scenarios.
Property-based tests verify subset and structural invariants.
"""

from tools.mock_data import (
    search_employees,
    get_equipment_recommendations,
    check_equipment_availability,
    EMPLOYEES,
    ROLE_EQUIPMENT_MAP,
    IT_INVENTORY,
)

from hypothesis import given, settings, strategies as st


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ALL_DEPARTMENTS = list({emp["department"] for emp in EMPLOYEES})

# Collect all valid equipment IDs across all categories
ALL_EQUIPMENT_IDS = []
for category, items in IT_INVENTORY.items():
    ALL_EQUIPMENT_IDS.extend(items.keys())


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

query_text = st.text(min_size=0, max_size=50)
department_sampler = st.sampled_from(ALL_DEPARTMENTS)
equipment_id_lists = st.lists(
    st.one_of(
        st.sampled_from(ALL_EQUIPMENT_IDS),
        st.text(min_size=1, max_size=30),
    ),
    min_size=0,
    max_size=10,
    unique=True,
)


# ===========================================================================
# Example-based tests (Task 5.1)
# ===========================================================================


def test_search_by_name():
    """Known employee name returns that employee."""
    results = search_employees("Lisa Chen")
    names = [emp["name"] for emp in results]
    assert "Lisa Chen" in names


def test_search_by_department():
    """Department filter restricts results to that department."""
    results = search_employees("", department="Engineering")
    for emp in results:
        assert emp["department"] == "Engineering"


def test_search_by_role():
    """Role filter restricts results to titles containing the role string."""
    results = search_employees("", role="Manager")
    for emp in results:
        assert "manager" in emp["title"].lower()


def test_search_no_match():
    """Nonsense query returns empty list."""
    results = search_employees("zzzznonexistent12345")
    assert results == []


def test_recommendations_known_role():
    """Known role returns the correct mapping and matched role key."""
    mapping, matched_role = get_equipment_recommendations("Data Scientist")
    assert matched_role == "Data Scientist"
    assert mapping == ROLE_EQUIPMENT_MAP["Data Scientist"]


def test_recommendations_unknown_role():
    """Unknown role defaults to Software Engineer."""
    mapping, matched_role = get_equipment_recommendations("Chief Happiness Officer")
    assert matched_role == "Software Engineer"
    assert mapping == ROLE_EQUIPMENT_MAP["Software Engineer"]


def test_availability_valid_ids():
    """Valid equipment IDs return full info dicts."""
    ids = ["macbook_pro_m3_16gb", "27_inch_4k"]
    result = check_equipment_availability(ids)
    for eq_id in ids:
        entry = result[eq_id]
        assert "category" in entry
        assert "available" in entry
        assert "stock" in entry
        assert "delivery_days" in entry
        assert "name" in entry
        assert "specs" in entry


def test_availability_invalid_id():
    """Unknown equipment ID returns error entry."""
    result = check_equipment_availability(["nonexistent_item_xyz"])
    entry = result["nonexistent_item_xyz"]
    assert entry["available"] is False
    assert "error" in entry


# ===========================================================================
# Property-based tests (Task 5.2)
# ===========================================================================


@given(query=query_text)
@settings(max_examples=100)
def test_prop_search_results_subset(query):
    """Property 7: search_employees results are a subset of EMPLOYEES.

    Feature: expand-test-coverage, Property 7: search_employees results are a subset of EMPLOYEES
    """
    results = search_employees(query)
    for emp in results:
        assert emp in EMPLOYEES


@given(query=query_text, department=department_sampler)
@settings(max_examples=100)
def test_prop_department_filter_respected(query, department):
    """Property 8: Department filter is always respected.

    Feature: expand-test-coverage, Property 8: Department filter is always respected
    """
    results = search_employees(query, department=department)
    for emp in results:
        assert emp["department"].lower() == department.lower()


@given(role=st.text(min_size=0, max_size=50))
@settings(max_examples=100)
def test_prop_recommendations_valid_role_key(role):
    """Property 9: get_equipment_recommendations always returns a valid role key.

    Feature: expand-test-coverage, Property 9: get_equipment_recommendations always returns a valid role key
    """
    _, matched_role = get_equipment_recommendations(role)
    assert matched_role in ROLE_EQUIPMENT_MAP


@given(ids=equipment_id_lists)
@settings(max_examples=100)
def test_prop_availability_keys_match_input(ids):
    """Property 10: check_equipment_availability output keys match input IDs.

    Feature: expand-test-coverage, Property 10: check_equipment_availability output keys match input IDs
    """
    result = check_equipment_availability(ids)
    assert set(result.keys()) == set(ids)
