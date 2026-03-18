"""
MIGRATION PATCH - How to Update telegram_prospecting_bot.py
This shows the exact changes needed to integrate the new testimonial search system.
"""

# ============================================================================
# STEP 1: ADD IMPORT AT TOP OF FILE (around line 1-50)
# ============================================================================

# OLD CODE (DELETE):
# from testimonial_search import search_testimonials, expand_search_keywords
# ... or similar

# NEW CODE (ADD):
from testimonial_search_refactored import (
    load_testimonials_from_cache,
    get_testimonials_for_prospect,
    CATEGORY_FALLBACKS,
)


# ============================================================================
# STEP 2: FIND & REPLACE TESTIMONIALS LOADING (around line 2614)
# ============================================================================

# OLD CODE TO REPLACE:
"""
def load_testimonials():
    '''Load testimonials from cache.'''
    if TESTIMONIALS_CACHE.exists():
        with open(TESTIMONIALS_CACHE) as f:
            return json.load(f)
    return []

TESTIMONIALS = load_testimonials()
"""

# NEW CODE:
"""
def load_testimonials():
    '''Load testimonials from cache.'''
    return load_testimonials_from_cache()

TESTIMONIALS = load_testimonials()
"""

# Or even simpler - just replace the module-level call:
# TESTIMONIALS = load_testimonials_from_cache()


# ============================================================================
# STEP 3: DELETE THESE OLD FUNCTIONS (around line 2620-2700)
# ============================================================================

# DELETE:
# - expand_search_keywords() - NOT USED IN NEW SYSTEM
# - search_testimonials() - REPLACED WITH NEW FUNCTION
# - OLD get_testimonials_for_prospect() - SIGNATURE CHANGED


# ============================================================================
# STEP 4: FIND ALL CALLS TO get_testimonials_for_prospect()
# ============================================================================

# Command to find them:
# grep -n "get_testimonials_for_prospect" telegram_prospecting_bot.py

# Example search result:
# 2750: results = get_testimonials_for_prospect(prospect)
# 3100: testimonials = get_testimonials_for_prospect(ctx_prospect, limit=5)
# etc.


# ============================================================================
# STEP 5: UPDATE EACH CALL SITE
# ============================================================================

# *** CRITICAL: Each call needs category + subcategory ***

# EXAMPLE 1: In a handler that has prospect data
# ============================================================================

# BEFORE:
def send_prospect_details(update, context, prospect):
    """OLD VERSION"""
    business_name = prospect.get('name', 'Unknown')
    # ... get more prospect details ...
    
    # OLD: No category info
    testimonials = get_testimonials_for_prospect(prospect, limit=3)
    
    if testimonials:
        message = f"Testimonials for {business_name}:\n"
        for t in testimonials:
            message += f"  • {t['business']}: {t['comment'][:50]}...\n"
    # ... send message ...


# AFTER:
def send_prospect_details(update, context, prospect):
    """NEW VERSION"""
    business_name = prospect.get('name', 'Unknown')
    category = prospect.get('category', '')  # ← Must have this
    subcategory = prospect.get('subcategory', '')  # ← Must have this
    
    # NEW: Include category + subcategory
    testimonials = get_testimonials_for_prospect(
        prospect,
        category=category,
        subcategory=subcategory,
        limit=3
    )
    
    if testimonials:
        message = f"Testimonials for {business_name}:\n"
        for t in testimonials:
            message += f"  • {t['business']}: {t['comment'][:50]}...\n"
    # ... send message ...


# ============================================================================
# EXAMPLE 2: When building prospect message
# ============================================================================

# BEFORE:
prospect_dict = {
    'name': 'Mountain View Dental',
    'city': 'Portland',
    'state': 'OR',
    'phone': '503-555-1234',
}

# Get testimonials
testimonials = get_testimonials_for_prospect(prospect_dict)


# AFTER:
prospect_dict = {
    'name': 'Mountain View Dental',
    'category': '🏥 Health/Medical',      # ← Add this
    'subcategory': 'Dentist',             # ← Add this
    'city': 'Portland',
    'state': 'OR',
    'phone': '503-555-1234',
}

# Get testimonials
testimonials = get_testimonials_for_prospect(
    prospect_dict,
    category=prospect_dict.get('category', ''),
    subcategory=prospect_dict.get('subcategory', ''),
)


# ============================================================================
# EXAMPLE 3: When category comes from context
# ============================================================================

# BEFORE:
async def show_prospect_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show prospect details - OLD"""
    prospect = context.user_data.get('current_prospect')
    
    # Get testimonials without category awareness
    testimonials = get_testimonials_for_prospect(prospect)
    
    # Send result...


# AFTER:
async def show_prospect_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show prospect details - NEW"""
    prospect = context.user_data.get('current_prospect')
    category = context.user_data.get('selected_category')  # ← Store this
    subcategory = context.user_data.get('selected_subcategory')  # ← Store this
    
    # Get testimonials with category awareness
    testimonials = get_testimonials_for_prospect(
        prospect,
        category=category,
        subcategory=subcategory,
    )
    
    # Send result...


# ============================================================================
# STEP 6: ENSURE PROSPECT DATA HAS CATEGORY + SUBCATEGORY
# ============================================================================

# When loading prospects, make sure they have category info:

# BEFORE:
prospects_from_api = [
    {'id': '1', 'name': 'Mountain View Dental', 'city': 'Portland', ...},
    {'id': '2', 'name': 'Happy Paws Grooming', 'city': 'Portland', ...},
]

# AFTER (enriched with categories):
prospects_from_api = [
    {
        'id': '1',
        'name': 'Mountain View Dental',
        'category': '🏥 Health/Medical',  # ← Added
        'subcategory': 'Dentist',         # ← Added
        'city': 'Portland',
        ...
    },
    {
        'id': '2',
        'name': 'Happy Paws Grooming',
        'category': '🏠 Pet Care',        # ← Added
        'subcategory': 'Dog Grooming',    # ← Added
        'city': 'Portland',
        ...
    },
]


# ============================================================================
# STEP 7: HOW TO DETERMINE CATEGORY FOR A PROSPECT
# ============================================================================

# Option 1: From Google Places API (if available)
def get_category_from_google_place(place_type):
    """Map Google Places types to our categories"""
    mapping = {
        'dental': ('🏥 Health/Medical', 'Dentist'),
        'dog_groomer': ('🏠 Pet Care', 'Dog Grooming'),
        'plumber': ('🔧 Home Services', 'Plumbing'),
        'hair_salon': ('💄 Beauty & Wellness', 'Hair Salon'),
        'restaurant': ('🍽️ Restaurants', 'All Restaurants'),
        # ... etc
    }
    return mapping.get(place_type, ('', ''))

# Option 2: From user selection in bot (category/subcategory flow)
def handle_category_selection(update, context, selected_category):
    """User selected a category - store it"""
    context.user_data['selected_category'] = selected_category
    # e.g., "🏥 Health/Medical"

def handle_subcategory_selection(update, context, selected_subcategory):
    """User selected a subcategory - store it"""
    context.user_data['selected_subcategory'] = selected_subcategory
    # e.g., "Dentist"

# Option 3: Infer from business name (less reliable but works for testing)
def infer_category_from_name(business_name):
    """Try to infer category from business name - fallback only"""
    from testimonial_search_refactored import extract_business_keyword
    
    keyword = extract_business_keyword(business_name)
    
    # Map keyword to category/subcategory
    if keyword in ['dental', 'dentist']:
        return ('🏥 Health/Medical', 'Dentist')
    elif keyword in ['grooming', 'dog', 'paws']:
        return ('🏠 Pet Care', 'Dog Grooming')
    elif keyword == 'plumbing':
        return ('🔧 Home Services', 'Plumbing')
    # ... etc
    
    return ('', '')  # Unknown


# ============================================================================
# STEP 8: TESTING YOUR CHANGES
# ============================================================================

# After making all changes, test with:

def test_integration():
    """Test that changes work correctly"""
    from testimonial_search_refactored import get_testimonials_for_prospect
    
    # Test 1: Dental prospect
    dental_prospect = {
        'name': 'Mountain View Dental',
        'category': '🏥 Health/Medical',
        'subcategory': 'Dentist',
    }
    
    results = get_testimonials_for_prospect(
        dental_prospect,
        category='🏥 Health/Medical',
        subcategory='Dentist',
    )
    
    assert len(results) <= 3, f"Expected ≤3 results, got {len(results)}"
    
    for r in results:
        # Check that results don't contain exclusion keywords
        assert 'grooming' not in r.get('searchable', '').lower()
        assert 'dog' not in r.get('searchable', '').lower()
    
    print("✅ Dental search test passed")
    
    # Test 2: Dog grooming prospect
    grooming_prospect = {
        'name': 'Happy Paws Grooming',
        'category': '🏠 Pet Care',
        'subcategory': 'Dog Grooming',
    }
    
    results = get_testimonials_for_prospect(
        grooming_prospect,
        category='🏠 Pet Care',
        subcategory='Dog Grooming',
    )
    
    for r in results:
        # Check that results don't contain exclusion keywords
        assert 'dental' not in r.get('searchable', '').lower()
        assert 'plumbing' not in r.get('searchable', '').lower()
    
    print("✅ Dog grooming search test passed")
    print("✅ All integration tests passed!")

if __name__ == "__main__":
    test_integration()


# ============================================================================
# STEP 9: FULL EXAMPLE - UPDATED HANDLER
# ============================================================================

async def handle_show_prospect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Complete example showing how to update a prospect display handler.
    This is what your actual handlers should look like after migration.
    """
    query = update.callback_query
    
    # Get prospect from context (stored earlier)
    prospect = context.user_data.get('current_prospect')
    category = context.user_data.get('selected_category')
    subcategory = context.user_data.get('selected_subcategory')
    
    if not prospect or not category or not subcategory:
        await query.answer("❌ Missing prospect information")
        return
    
    # Get testimonials using NEW function with category info
    testimonials = get_testimonials_for_prospect(
        prospect,
        category=category,
        subcategory=subcategory,
        limit=3
    )
    
    # Build message
    business_name = prospect.get('name', 'Unknown')
    message = f"<b>{business_name}</b>\n\n"
    
    if testimonials:
        message += "<b>Recent Testimonials:</b>\n"
        for i, t in enumerate(testimonials, 1):
            company = t.get('business', 'Unknown')
            comment = t.get('comment', '')[:100]
            message += f"\n{i}. <i>{company}</i>\n\"{comment}...\"\n"
    else:
        message += "No testimonials found in this category.\n"
    
    # Send
    await query.edit_message_text(message, parse_mode='HTML')


# ============================================================================
# SUMMARY OF CHANGES
# ============================================================================

"""
CHECKLIST FOR MIGRATION:

1. ☐ Add import statement at top of file
   from testimonial_search_refactored import (...)

2. ☐ Update load_testimonials() to use load_testimonials_from_cache()

3. ☐ Delete old functions:
   - expand_search_keywords()
   - search_testimonials()
   - OLD get_testimonials_for_prospect()

4. ☐ Find all call sites:
   grep -n "get_testimonials_for_prospect" telegram_prospecting_bot.py

5. ☐ Update EACH call with category + subcategory:
   OLD: get_testimonials_for_prospect(prospect)
   NEW: get_testimonials_for_prospect(prospect, category=cat, subcategory=subcat)

6. ☐ Ensure prospect data includes 'category' and 'subcategory' fields

7. ☐ Test with example prospects from each category

8. ☐ Run full test suite:
   python3 scripts/test_testimonial_search.py

9. ☐ Deploy and monitor for issues

10. ☐ Commit with message like:
    "refactor: integrate new category-aware testimonial search
    
    - Update all get_testimonials_for_prospect() calls with category info
    - Remove old expand_search_keywords() and search_testimonials()
    - Ensure all prospects have category/subcategory fields
    - All tests passing (8/8)"
"""
