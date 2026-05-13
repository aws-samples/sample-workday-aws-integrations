# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Tests for tools/hr_tools.py

Example-based tests for EmployeeDirectoryTool and ITAssetTool.
No property tests — these are thin wrappers over mock_data.py
which is already property-tested in test_mock_data.py.
"""

from tools.hr_tools import EmployeeDirectoryTool, ITAssetTool


# ===========================================================================
# EmployeeDirectoryTool tests
# ===========================================================================


def test_employee_lookup_basic():
    """Query returns response with results_count and employees list."""
    result = EmployeeDirectoryTool.execute(query="Lisa Chen")
    assert "results_count" in result
    assert "employees" in result
    assert isinstance(result["employees"], list)
    assert result["results_count"] > 0


def test_employee_lookup_mentor_filter():
    """find_mentor=True returns only employees with mentor_available=True."""
    result = EmployeeDirectoryTool.execute(query="Engineering", find_mentor=True)
    for emp in result["employees"]:
        assert emp["mentor_available"] is True


def test_employee_lookup_manager_filter():
    """find_manager=True returns only employees with 'manager' in title."""
    result = EmployeeDirectoryTool.execute(query="Engineering", find_manager=True)
    for emp in result["employees"]:
        assert "manager" in emp["title"].lower()


def test_employee_lookup_no_results():
    """No-match query returns results_count=0 and empty employees list."""
    result = EmployeeDirectoryTool.execute(query="zzzznonexistent12345")
    assert result["results_count"] == 0
    assert result["employees"] == []


# ===========================================================================
# ITAssetTool tests
# ===========================================================================


def test_it_asset_get_recommendations():
    """action=get_recommendations returns laptop, monitor, accessories."""
    result = ITAssetTool.execute(action="get_recommendations", role="Software Engineer")
    assert "recommendations" in result
    recs = result["recommendations"]
    assert "laptop" in recs
    assert "monitor" in recs
    assert "accessories" in recs


def test_it_asset_check_availability():
    """action=check_availability returns availability dict and summary."""
    result = ITAssetTool.execute(action="check_availability", role="Software Engineer")
    assert "availability" in result
    assert "summary" in result
    summary = result["summary"]
    assert "total_items" in summary
    assert "available_items" in summary
    assert "out_of_stock" in summary


def test_it_asset_create_request():
    """action=create_request returns request_id, status, items, cost."""
    result = ITAssetTool.execute(action="create_request", role="Software Engineer")
    assert "request_id" in result
    assert result["status"] == "submitted"
    assert "requested_items" in result
    assert isinstance(result["requested_items"], list)
    assert "total_cost" in result


def test_it_asset_unknown_action():
    """Unknown action returns error key."""
    result = ITAssetTool.execute(action="nonexistent_action", role="Software Engineer")
    assert "error" in result
