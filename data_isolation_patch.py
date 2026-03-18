"""
Data Isolation & Security Patch for IndoorMediaProspectBot

This patch implements:
1. Data isolation by rep_id (security-critical)
2. Email permission gating for contracts
3. Selective calendar invites (Tyler's team only)
4. TYLER_TEAM list for easy management

Installation:
  1. Add this file to scripts/ directory
  2. Import these functions at the top of telegram_prospecting_bot.py
  3. Replace all data access calls with the isolated versions
"""

from typing import Dict, List, Optional
from pathlib import Path
import json

# =======================================================================================
# TYLER'S DIRECT TEAM - Editable list for selective calendar invites
# =======================================================================================

TYLER_TEAM = [
    "Adan",
    "Ben",
    "Amy", 
    "Dave",
    "Christian",
    "Megan",
    "Marty",
    "Matt",
    "Jan",
]

# =======================================================================================
# SHARED ACCESS & ADMIN PERMISSIONS
# =======================================================================================

def load_shared_access_config() -> Dict:
    """Load shared access configuration."""
    try:
        workspace = Path(__file__).parent
        config_file = workspace / "data" / "shared_access.json"
        if config_file.exists():
            with open(config_file) as f:
                return json.load(f)
    except Exception:
        pass
    return {"shared_access_pairs": [], "admin_ids": []}


def get_accessible_rep_ids(rep_id: str, registry: Dict) -> List[str]:
    """Get all rep IDs this user can access (includes themselves, shared pairs, and admin access)."""
    rep_ids = [str(rep_id)]
    
    config = load_shared_access_config()
    rep_email = registry.get(str(rep_id), {}).get("email", "")
    
    # Check if admin
    if str(rep_id) in config.get("admin_ids", []):
        # Admin sees all reps - return all rep IDs
        return list(registry.keys())
    
    # Check for shared access pairs
    for pair in config.get("shared_access_pairs", []):
        rep1_email = pair.get("rep_1", "").lower()
        rep2_email = pair.get("rep_2", "").lower()
        current_email = rep_email.lower()
        
        if current_email == rep1_email:
            # Find rep2's ID
            for rid, rdata in registry.items():
                if rdata.get("email", "").lower() == rep2_email:
                    rep_ids.append(str(rid))
        elif current_email == rep2_email:
            # Find rep1's ID
            for rid, rdata in registry.items():
                if rdata.get("email", "").lower() == rep1_email:
                    rep_ids.append(str(rid))
    
    return rep_ids


# =======================================================================================
# DATA ISOLATION HELPERS - Enforce rep_id filtering on all data access
# =======================================================================================

def get_saved_prospects(rep_id: str, data: Dict, registry: Dict = None) -> Dict:
    """Get saved prospects this rep can access (includes shared access)."""
    if registry is None:
        registry = {}
    
    accessible_ids = get_accessible_rep_ids(rep_id, registry)
    all_prospects = {}
    
    for rid in accessible_ids:
        rep_data = data.get("reps", {}).get(str(rid), {})
        all_prospects.update(rep_data.get("saved_prospects", {}))
    
    return all_prospects

def get_customer_list(rep_id: str, data: Dict, registry: Dict = None) -> Dict:
    """Get customer pipeline this rep can access (includes shared access)."""
    if registry is None:
        registry = {}
    
    saved = get_saved_prospects(rep_id, data, registry)
    return {k: v for k, v in saved.items() if v.get("status") in ["follow-up", "proposal", "interested"]}

def get_search_history(rep_id: str, data: Dict, registry: Dict = None) -> List:
    """Get search history this rep can access (includes shared access)."""
    if registry is None:
        registry = {}
    
    accessible_ids = get_accessible_rep_ids(rep_id, registry)
    all_history = []
    
    for rid in accessible_ids:
        rep_data = data.get("reps", {}).get(str(rid), {})
        all_history.extend(rep_data.get("search_history", []))
    
    return all_history

def get_contact_history(rep_id: str, data: Dict) -> Dict:
    """Get ONLY this rep's contact history."""
    rep_data = data.get("reps", {}).get(str(rep_id), {})
    return rep_data.get("contact_history", {})

def save_prospect(rep_id: str, prospect_id: str, prospect_data: Dict, data: Dict):
    """Save a prospect to ONLY this rep's saved_prospects."""
    if str(rep_id) not in data["reps"]:
        data["reps"][str(rep_id)] = {
            "name": "",
            "status": "approved",
            "email": "",
            "email_permission": False,
            "saved_prospects": {},
            "search_history": [],
            "contact_history": {},
        }
    
    data["reps"][str(rep_id)]["saved_prospects"][prospect_id] = prospect_data
    return True

def add_to_search_history(rep_id: str, search_query: str, data: Dict):
    """Add to ONLY this rep's search history."""
    if str(rep_id) not in data["reps"]:
        data["reps"][str(rep_id)] = {
            "name": "",
            "status": "approved",
            "email": "",
            "email_permission": False,
            "saved_prospects": {},
            "search_history": [],
            "contact_history": {},
        }
    
    data["reps"][str(rep_id)]["search_history"].append(search_query)
    return True

def add_to_contact_history(rep_id: str, prospect_id: str, contact_info: Dict, data: Dict):
    """Add to ONLY this rep's contact history."""
    if str(rep_id) not in data["reps"]:
        data["reps"][str(rep_id)] = {
            "name": "",
            "status": "approved",
            "email": "",
            "email_permission": False,
            "saved_prospects": {},
            "search_history": [],
            "contact_history": {},
        }
    
    data["reps"][str(rep_id)]["contact_history"][prospect_id] = contact_info
    return True

def bookmark_prospect(rep_id: str, prospect_id: str, data: Dict):
    """Bookmark a prospect for ONLY this rep."""
    saved = get_saved_prospects(rep_id, data)
    if prospect_id in saved:
        saved[prospect_id]["bookmarked"] = True
        return True
    return False

# =======================================================================================
# EMAIL PERMISSION GATING - Check before allowing contract access
# =======================================================================================

def can_access_contracts(rep_id: str, data: Dict) -> bool:
    """Check if rep has granted email permission to access contracts."""
    rep_data = data.get("reps", {}).get(str(rep_id), {})
    return rep_data.get("email_permission", False)

def get_email_permission_status(rep_id: str, data: Dict) -> Dict:
    """Get email permission info for a rep."""
    rep_data = data.get("reps", {}).get(str(rep_id), {})
    return {
        "granted": rep_data.get("email_permission", False),
        "email": rep_data.get("email", ""),
        "account_email": rep_data.get("account_email", ""),
    }

# =======================================================================================
# CALENDAR INVITE FILTERING - Only invite Tyler for his direct team
# =======================================================================================

def should_invite_tyler_to_calendar(rep_name: str) -> bool:
    """
    Determine if Tyler should be invited to calendar event.
    
    Only invites if rep is part of his direct team.
    """
    # Normalize rep name for matching (handle "Megan Wink" vs "Meghan Wink", etc.)
    normalized = rep_name.strip().split()[0] if rep_name else ""
    
    for team_member in TYLER_TEAM:
        if normalized.lower() == team_member.lower():
            return True
    
    return False

def get_calendar_attendees(rep_name: str, base_attendees: List[str] = None) -> List[str]:
    """
    Get attendees list for calendar event.
    
    Returns list with Tyler's email if he's on the direct team.
    """
    attendees = base_attendees or []
    
    if should_invite_tyler_to_calendar(rep_name):
        if "tyler.vansant@indoormedia.com" not in attendees:
            attendees.append("tyler.vansant@indoormedia.com")
    
    return attendees

# =======================================================================================
# DATA STRUCTURE VALIDATION - Ensure new fields exist
# =======================================================================================

def ensure_rep_fields(rep_data: Dict) -> Dict:
    """Ensure all required fields exist in rep data."""
    defaults = {
        "name": "",
        "status": "approved",
        "email": "",
        "account_email": "",
        "email_permission": False,
        "saved_prospects": {},
        "search_history": [],
        "contact_history": {},
        "session_searches": 0,
        "session_bookmarks": 0,
    }
    
    for key, default_val in defaults.items():
        if key not in rep_data:
            rep_data[key] = default_val
    
    return rep_data

def ensure_prospect_fields(prospect_data: Dict) -> Dict:
    """Ensure all required fields exist in prospect data."""
    defaults = {
        "name": "",
        "address": "",
        "phone": "",
        "email": "",
        "contact_name": "",
        "score": 0,
        "status": "interested",  # interested, follow-up, proposal, closed
        "saved_date": "",
        "last_contacted": None,
        "visit_count": 0,
        "notes": [],
        "bookmarked": False,
    }
    
    for key, default_val in defaults.items():
        if key not in prospect_data:
            prospect_data[key] = default_val
    
    return prospect_data
