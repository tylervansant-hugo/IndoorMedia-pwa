"""
Integration patch for smart upsell emails in telegram_prospecting_bot.py

This file shows how to integrate the upsell_email_system into the main bot.

INSTALLATION:
1. Add import at top of telegram_prospecting_bot.py:
   from upsell_email_system import (
       get_upsell_email_params_from_contract,
       draft_smart_upsell_email,
   )

2. Replace the upsell email handler (around line 6628) with:

   elif template_type == "upsell":
       # Get smart upsell parameters from contract if available
       contract_number = c.get('contract_number', '')
       
       if contract_number:
           # Use smart upsell system with product tracking
           upsell_params = get_upsell_email_params_from_contract(contract_number)
           if upsell_params:
               body = draft_smart_upsell_email(
                   business_name=business,
                   owner_name=owner,
                   rep_name=rep_name,
                   store_ref=store,
                   contract_number=contract_number,
                   address=upsell_params.get('address', ''),
                   current_chain=upsell_params.get('store_name', '')
               )
           else:
               # Fall back to basic upsell email
               body = draft_upsell_email(business, owner, rep_name, store)
       else:
           # No contract number - use basic version
           body = draft_upsell_email(business, owner, rep_name, store)
       
       subject = f"Expansion Opportunity — {business}"

This replaces the old single-line call with intelligent product and store suggestions.
"""

# Example of how the new function works:

def show_example():
    from upsell_email_system import get_upsell_email_params_from_contract, draft_smart_upsell_email
    
    # When a rep clicks "Draft Email" on a customer with contract J426747E:
    contract_number = "J426747E"
    
    # Get all the smart parameters
    params = get_upsell_email_params_from_contract(contract_number)
    
    print(f"Customer: {params['business_name']}")
    print(f"Contact: {params['contact_name']}")
    print(f"Signed up for: {params['signed_up_for']}")
    print(f"Current location: {params['store_name']}")
    
    # Generate the smart email
    email = draft_smart_upsell_email(
        business_name=params['business_name'],
        owner_name=params['contact_name'],
        rep_name="Tyler VanSant",
        store_ref=f"{params['store_name']}",
        contract_number=contract_number,
        address=params['address'],
        current_chain=params['store_name']
    )
    
    print("\n=== GENERATED EMAIL ===")
    print(email)
    
    # Shows nearby stores automatically included in the email
    print("\n=== NEARBY STORES CONSIDERED ===")
    for store in params['nearby_stores'][:3]:
        print(f"• {store['GroceryChain']} in {store['City']}")

if __name__ == "__main__":
    show_example()
