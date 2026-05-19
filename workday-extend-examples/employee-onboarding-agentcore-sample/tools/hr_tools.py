# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
HR Tools for the onboarding demo.
These tools simulate employee directory and IT asset management systems.
"""

import json
from typing import Dict, List, Any, Optional
from .mock_data import (
    search_employees, 
    get_equipment_recommendations, 
    check_equipment_availability,
    IT_INVENTORY,
    OFFICE_LOCATIONS
)

class EmployeeDirectoryTool:
    """Tool for looking up employee information."""
    
    @staticmethod
    def get_schema():
        return {
            "name": "employee_lookup",
            "description": "Look up employee information by name, department, or role for manager assignment and team introductions",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (name, department, role, or specialty)"
                    },
                    "department": {
                        "type": "string", 
                        "description": "Filter by department (optional)"
                    },
                    "role": {
                        "type": "string",
                        "description": "Filter by role/title (optional)"
                    },
                    "find_manager": {
                        "type": "boolean",
                        "description": "Whether to find managers specifically (optional)"
                    },
                    "find_mentor": {
                        "type": "boolean", 
                        "description": "Whether to find available mentors (optional)"
                    }
                },
                "required": ["query"]
            }
        }
    
    @staticmethod
    def execute(query: str, department: Optional[str] = None, role: Optional[str] = None, 
                find_manager: bool = False, find_mentor: bool = False) -> Dict[str, Any]:
        """Execute employee lookup."""
        
        # If looking for managers, modify query
        if find_manager:
            if "manager" not in query.lower():
                query += " manager"
        
        # Search employees
        results = search_employees(query, department, role)
        
        # Filter for mentors if requested
        if find_mentor:
            results = [emp for emp in results if emp.get("mentor_capacity", False)]
        
        # Filter for managers if requested  
        if find_manager:
            results = [emp for emp in results if "manager" in emp["title"].lower()]
        
        # Format response
        response = {
            "query": query,
            "filters": {
                "department": department,
                "role": role,
                "find_manager": find_manager,
                "find_mentor": find_mentor
            },
            "results_count": len(results),
            "employees": []
        }
        
        for emp in results[:5]:  # Limit to top 5 results
            emp_info = {
                "name": emp["name"],
                "title": emp["title"], 
                "department": emp["department"],
                "email": emp["email"],
                "location": emp["location"],
                "manager": emp["manager"],
                "reports": emp.get("reports", 0),
                "specialties": emp["specialties"],
                "mentor_available": emp.get("mentor_capacity", False),
                "buddy_available": emp.get("buddy_available", False),
                "start_date": emp["start_date"]
            }
            response["employees"].append(emp_info)
        
        return response

class ITAssetTool:
    """Tool for IT equipment management."""
    
    @staticmethod
    def get_schema():
        return {
            "name": "it_asset_check", 
            "description": "Check IT equipment availability and create provisioning requests based on employee role",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["check_availability", "get_recommendations", "create_request"],
                        "description": "Action to perform"
                    },
                    "role": {
                        "type": "string",
                        "description": "Employee role for equipment recommendations"
                    },
                    "location": {
                        "type": "string",
                        "description": "Office location for delivery (optional)"
                    },
                    "equipment_type": {
                        "type": "string", 
                        "enum": ["laptop", "monitor", "accessories", "all"],
                        "description": "Type of equipment to check (optional)"
                    },
                    "specific_items": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific equipment IDs to check (optional)"
                    }
                },
                "required": ["action", "role"]
            }
        }
    
    @staticmethod
    def execute(action: str, role: str, location: Optional[str] = None, 
                equipment_type: Optional[str] = None, specific_items: Optional[List[str]] = None) -> Dict[str, Any]:
        """Execute IT asset management action."""
        
        if action == "get_recommendations":
            return ITAssetTool._get_recommendations(role, location)
        elif action == "check_availability":
            return ITAssetTool._check_availability(role, equipment_type, specific_items, location)
        elif action == "create_request":
            return ITAssetTool._create_request(role, location)
        else:
            return {"error": f"Unknown action: {action}"}
    
    @staticmethod
    def _get_recommendations(role: str, location: Optional[str] = None) -> Dict[str, Any]:
        """Get equipment recommendations for a role."""
        recommendations, matched_role = get_equipment_recommendations(role)
        
        response = {
            "action": "get_recommendations",
            "input_role": role,
            "matched_role": matched_role,
            "location": location or "Seattle Office",
            "recommendations": {
                "laptop": None,
                "monitor": None, 
                "accessories": []
            }
        }
        
        # Get laptop details
        if recommendations["laptop"] in IT_INVENTORY["laptops"]:
            laptop = IT_INVENTORY["laptops"][recommendations["laptop"]]
            response["recommendations"]["laptop"] = {
                "id": recommendations["laptop"],
                "name": laptop["name"],
                "specs": laptop["specs"],
                "available": laptop["stock"] > 0,
                "stock": laptop["stock"]
            }
        
        # Get monitor details
        if recommendations["monitor"] in IT_INVENTORY["monitors"]:
            monitor = IT_INVENTORY["monitors"][recommendations["monitor"]]
            response["recommendations"]["monitor"] = {
                "id": recommendations["monitor"],
                "name": monitor["name"],
                "specs": monitor["specs"],
                "available": monitor["stock"] > 0,
                "stock": monitor["stock"]
            }
        
        # Get accessories details
        for acc_id in recommendations["accessories"]:
            if acc_id in IT_INVENTORY["accessories"]:
                acc = IT_INVENTORY["accessories"][acc_id]
                response["recommendations"]["accessories"].append({
                    "id": acc_id,
                    "name": acc["name"],
                    "specs": acc["specs"],
                    "available": acc["stock"] > 0,
                    "stock": acc["stock"]
                })
        
        return response
    
    @staticmethod
    def _check_availability(role: str, equipment_type: Optional[str] = None, 
                           specific_items: Optional[List[str]] = None, 
                           location: Optional[str] = None) -> Dict[str, Any]:
        """Check equipment availability."""
        
        if specific_items:
            # Check specific items
            availability = check_equipment_availability(specific_items)
        else:
            # Get recommendations and check those
            recommendations, matched_role = get_equipment_recommendations(role)
            items_to_check = []
            
            if not equipment_type or equipment_type in ["laptop", "all"]:
                items_to_check.append(recommendations["laptop"])
            if not equipment_type or equipment_type in ["monitor", "all"]:
                items_to_check.append(recommendations["monitor"])
            if not equipment_type or equipment_type in ["accessories", "all"]:
                items_to_check.extend(recommendations["accessories"])
            
            availability = check_equipment_availability(items_to_check)
        
        # Calculate delivery times based on location
        location_info = OFFICE_LOCATIONS.get(location or "Seattle Office", OFFICE_LOCATIONS["Seattle Office"])
        delivery_modifier = location_info["delivery_days_modifier"]
        
        # Add delivery time adjustments
        for item_id, item_info in availability.items():
            if "delivery_days" in item_info:
                item_info["delivery_days"] += delivery_modifier
                item_info["delivery_location"] = location or "Seattle Office"
        
        response = {
            "action": "check_availability",
            "role": role,
            "equipment_type": equipment_type,
            "location": location or "Seattle Office",
            "availability": availability,
            "summary": {
                "total_items": len(availability),
                "available_items": len([item for item in availability.values() if item.get("available", False)]),
                "out_of_stock": len([item for item in availability.values() if not item.get("available", False)])
            }
        }
        
        return response
    
    @staticmethod
    def _create_request(role: str, location: Optional[str] = None) -> Dict[str, Any]:
        """Create an IT provisioning request."""
        import uuid
        from datetime import datetime, timedelta
        
        # Get recommendations
        recommendations, matched_role = get_equipment_recommendations(role)
        all_items = [recommendations["laptop"], recommendations["monitor"]] + recommendations["accessories"]
        
        # Check availability
        availability = check_equipment_availability(all_items)
        
        # Calculate delivery
        location_info = OFFICE_LOCATIONS.get(location or "Seattle Office", OFFICE_LOCATIONS["Seattle Office"])
        max_delivery_days = max([item.get("delivery_days", 1) for item in availability.values() if item.get("available", False)]) + location_info["delivery_days_modifier"]
        
        estimated_delivery = datetime.now() + timedelta(days=max_delivery_days)
        
        request_id = f"IT-REQ-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
        
        response = {
            "action": "create_request",
            "request_id": request_id,
            "role": role,
            "matched_role": matched_role,
            "location": location or "Seattle Office",
            "status": "submitted",
            "estimated_delivery": estimated_delivery.strftime("%Y-%m-%d"),
            "delivery_days": max_delivery_days,
            "requested_items": [],
            "total_cost": 0
        }
        
        # Add item details
        total_cost = 0
        for item_id in all_items:
            if item_id in availability and availability[item_id].get("available", False):
                # Find the item in inventory to get cost
                item_cost = 0
                for category, items in IT_INVENTORY.items():
                    if item_id in items:
                        item_cost = items[item_id]["cost"]
                        break
                
                response["requested_items"].append({
                    "id": item_id,
                    "name": availability[item_id]["name"],
                    "category": availability[item_id]["category"],
                    "cost": item_cost,
                    "delivery_days": availability[item_id]["delivery_days"]
                })
                total_cost += item_cost
        
        response["total_cost"] = total_cost
        
        return response

# Tool registry for easy access
HR_TOOLS = {
    "employee_lookup": EmployeeDirectoryTool,
    "it_asset_check": ITAssetTool
}