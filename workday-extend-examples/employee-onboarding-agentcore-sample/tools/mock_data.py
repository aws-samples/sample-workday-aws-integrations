# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Mock data for HR onboarding tools.
This simulates realistic employee directory and IT asset management systems.
"""

# Employee Directory Data
EMPLOYEES = [
    {
        "name": "Mike Johnson",
        "title": "Engineering Manager",
        "department": "Engineering", 
        "email": "mike.johnson@anycompany.com",
        "manager": "Sarah Williams",
        "location": "Seattle Office",
        "start_date": "2021-03-15",
        "reports": 8,
        "specialties": ["Team Leadership", "System Architecture", "Python"],
        "mentor_capacity": True,
        "buddy_available": False  # Too busy as manager
    },
    {
        "name": "Lisa Chen",
        "title": "Senior Software Engineer",
        "department": "Engineering",
        "email": "lisa.chen@anycompany.com", 
        "manager": "Mike Johnson",
        "location": "Seattle Office",
        "start_date": "2020-08-10",
        "reports": 0,
        "specialties": ["Python", "AWS", "Microservices", "Mentoring"],
        "mentor_capacity": True,
        "buddy_available": True
    },
    {
        "name": "David Rodriguez",
        "title": "Senior Data Scientist",
        "department": "Data Science",
        "email": "david.rodriguez@anycompany.com",
        "manager": "Jennifer Kim",
        "location": "San Francisco Office", 
        "start_date": "2019-11-20",
        "reports": 2,
        "specialties": ["Machine Learning", "Python", "SQL", "Statistics"],
        "mentor_capacity": True,
        "buddy_available": True
    },
    {
        "name": "Jennifer Kim",
        "title": "Data Science Manager",
        "department": "Data Science",
        "email": "jennifer.kim@anycompany.com",
        "manager": "Sarah Williams",
        "location": "San Francisco Office",
        "start_date": "2020-01-15", 
        "reports": 6,
        "specialties": ["Team Leadership", "ML Strategy", "Analytics"],
        "mentor_capacity": True,
        "buddy_available": False
    },
    {
        "name": "Alex Thompson",
        "title": "Product Manager",
        "department": "Product",
        "email": "alex.thompson@anycompany.com",
        "manager": "Rachel Davis",
        "location": "New York Office",
        "start_date": "2021-07-01",
        "reports": 0,
        "specialties": ["Product Strategy", "User Research", "Agile"],
        "mentor_capacity": True,
        "buddy_available": True
    },
    {
        "name": "Rachel Davis", 
        "title": "VP of Product",
        "department": "Product",
        "email": "rachel.davis@anycompany.com",
        "manager": "Sarah Williams",
        "location": "New York Office",
        "start_date": "2019-05-10",
        "reports": 12,
        "specialties": ["Product Leadership", "Strategy", "Growth"],
        "mentor_capacity": False,
        "buddy_available": False
    },
    {
        "name": "Sarah Williams",
        "title": "VP of Engineering",
        "department": "Engineering",
        "email": "sarah.williams@anycompany.com", 
        "manager": "CEO",
        "location": "Seattle Office",
        "start_date": "2018-02-01",
        "reports": 25,
        "specialties": ["Engineering Leadership", "Scaling Teams", "Architecture"],
        "mentor_capacity": False,
        "buddy_available": False
    }
]

# IT Equipment Inventory
IT_INVENTORY = {
    "laptops": {
        "macbook_pro_m3_16gb": {
            "name": "MacBook Pro M3 16GB",
            "stock": 15,
            "delivery_days": 1,
            "cost": 2499,
            "specs": "M3 chip, 16GB RAM, 512GB SSD"
        },
        "macbook_pro_m3_32gb": {
            "name": "MacBook Pro M3 32GB", 
            "stock": 8,
            "delivery_days": 2,
            "cost": 3199,
            "specs": "M3 chip, 32GB RAM, 1TB SSD"
        },
        "dell_xps_15": {
            "name": "Dell XPS 15",
            "stock": 25,
            "delivery_days": 1,
            "cost": 1899,
            "specs": "Intel i7, 16GB RAM, 512GB SSD"
        },
        "thinkpad_x1": {
            "name": "ThinkPad X1 Carbon",
            "stock": 12,
            "delivery_days": 3,
            "cost": 1699,
            "specs": "Intel i7, 16GB RAM, 256GB SSD"
        }
    },
    "monitors": {
        "27_inch_4k": {
            "name": "27-inch 4K Monitor",
            "stock": 22,
            "delivery_days": 1,
            "cost": 399,
            "specs": "27-inch, 4K resolution, USB-C"
        },
        "32_inch_ultrawide": {
            "name": "32-inch Ultrawide Monitor",
            "stock": 8,
            "delivery_days": 2,
            "cost": 699,
            "specs": "32-inch, 3440x1440, curved"
        },
        "24_inch_standard": {
            "name": "24-inch Standard Monitor",
            "stock": 35,
            "delivery_days": 1,
            "cost": 199,
            "specs": "24-inch, 1080p, HDMI/DisplayPort"
        }
    },
    "accessories": {
        "wireless_keyboard": {
            "name": "Wireless Mechanical Keyboard",
            "stock": 45,
            "delivery_days": 1,
            "cost": 129,
            "specs": "Mechanical switches, wireless"
        },
        "ergonomic_mouse": {
            "name": "Ergonomic Wireless Mouse", 
            "stock": 50,
            "delivery_days": 1,
            "cost": 79,
            "specs": "Ergonomic design, wireless"
        },
        "usb_c_dock": {
            "name": "USB-C Docking Station",
            "stock": 18,
            "delivery_days": 2,
            "cost": 199,
            "specs": "Multiple ports, 4K support"
        },
        "noise_canceling_headset": {
            "name": "Noise-Canceling Headset",
            "stock": 28,
            "delivery_days": 1,
            "cost": 249,
            "specs": "Active noise canceling, wireless"
        }
    }
}

# Role-based Equipment Recommendations
ROLE_EQUIPMENT_MAP = {
    "Software Engineer": {
        "laptop": "macbook_pro_m3_16gb",
        "monitor": "27_inch_4k", 
        "accessories": ["wireless_keyboard", "ergonomic_mouse", "usb_c_dock"]
    },
    "Senior Software Engineer": {
        "laptop": "macbook_pro_m3_32gb",
        "monitor": "32_inch_ultrawide",
        "accessories": ["wireless_keyboard", "ergonomic_mouse", "usb_c_dock", "noise_canceling_headset"]
    },
    "Data Scientist": {
        "laptop": "macbook_pro_m3_32gb",  # Need more RAM for ML
        "monitor": "27_inch_4k",
        "accessories": ["wireless_keyboard", "ergonomic_mouse", "usb_c_dock"]
    },
    "Product Manager": {
        "laptop": "macbook_pro_m3_16gb",
        "monitor": "24_inch_standard",
        "accessories": ["wireless_keyboard", "ergonomic_mouse"]
    },
    "Engineering Manager": {
        "laptop": "macbook_pro_m3_16gb", 
        "monitor": "27_inch_4k",
        "accessories": ["wireless_keyboard", "ergonomic_mouse", "usb_c_dock", "noise_canceling_headset"]
    },
    "Designer": {
        "laptop": "macbook_pro_m3_32gb",  # Need power for design work
        "monitor": "32_inch_ultrawide",   # Need screen real estate
        "accessories": ["wireless_keyboard", "ergonomic_mouse", "usb_c_dock"]
    }
}

# Office Locations
OFFICE_LOCATIONS = {
    "Seattle Office": {
        "address": "123 Tech Way, Seattle, WA 98101",
        "delivery_days_modifier": 0,  # Base delivery time
        "timezone": "Pacific"
    },
    "San Francisco Office": {
        "address": "456 Innovation Blvd, San Francisco, CA 94105", 
        "delivery_days_modifier": 1,  # +1 day for cross-state
        "timezone": "Pacific"
    },
    "New York Office": {
        "address": "789 Business Ave, New York, NY 10001",
        "delivery_days_modifier": 2,  # +2 days for cross-country
        "timezone": "Eastern"
    }
}

def search_employees(query, department=None, role=None):
    """Search employees by query string with optional filters."""
    results = []
    query_lower = query.lower()
    
    for emp in EMPLOYEES:
        # Check if query matches name, title, or specialties
        matches = (
            query_lower in emp["name"].lower() or
            query_lower in emp["title"].lower() or
            any(query_lower in spec.lower() for spec in emp["specialties"])
        )
        
        # Apply department filter
        if department and emp["department"].lower() != department.lower():
            matches = False
            
        # Apply role filter  
        if role and role.lower() not in emp["title"].lower():
            matches = False
            
        if matches:
            results.append(emp)
    
    return results

def get_equipment_recommendations(role):
    """Get equipment recommendations for a specific role."""
    role_key = None
    
    # Find matching role (case insensitive, partial match)
    for key in ROLE_EQUIPMENT_MAP.keys():
        if role.lower() in key.lower() or key.lower() in role.lower():
            role_key = key
            break
    
    if not role_key:
        # Default to Software Engineer if no match
        role_key = "Software Engineer"
    
    return ROLE_EQUIPMENT_MAP[role_key], role_key

def check_equipment_availability(equipment_ids):
    """Check availability for a list of equipment IDs."""
    availability = {}
    
    for eq_id in equipment_ids:
        # Search all categories for the equipment
        found = False
        for category, items in IT_INVENTORY.items():
            if eq_id in items:
                availability[eq_id] = {
                    "category": category,
                    "available": items[eq_id]["stock"] > 0,
                    "stock": items[eq_id]["stock"],
                    "delivery_days": items[eq_id]["delivery_days"],
                    "name": items[eq_id]["name"],
                    "specs": items[eq_id]["specs"]
                }
                found = True
                break
        
        if not found:
            availability[eq_id] = {
                "available": False,
                "error": "Equipment not found"
            }
    
    return availability