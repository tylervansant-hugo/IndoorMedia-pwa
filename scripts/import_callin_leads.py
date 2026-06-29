#!/usr/bin/env python3
"""
Auto-import IndoorMedia "New Call In Lead" emails into the PWA Hot Leads
under category "Call-In Lead".

Pipeline (matches the manual workflow built Jun 29, 2026):
  1. Search Gmail (tyler.vansant@indoormedia.com) for subject "New Call In Lead"
  2. Parse the structured lead block (Business/Customer/Phone/Email/Comments/Zip/CRM id)
  3. De-dupe against existing records by crm_id (and business+phone+zip)
  4. Zip -> lat/lng via pgeocode; nearest store via haversine vs public/data/stores.json
  5. Research each NEW business via Google Places searchText (GOOGLE_PLACES_API_KEY)
  6. Append new records to public/data/hot_leads.json with category "Call-In Lead"
  7. Build + deploy is handled by the caller (cron agent) — this script only writes data.

Run: python3 scripts/import_callin_leads.py [--max 80] [--dry-run]
Exit code 0 always; prints a JSON summary line prefixed with RESULT: for the agent.
"""
import os, re, json, math, time, ssl, subprocess, argparse, datetime, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOT_LEADS = os.path.join(ROOT, "public", "data", "hot_leads.json")
STORES = os.path.join(ROOT, "public", "data", "stores.json")
ACCOUNT = "tyler.vansant@indoormedia.com"

def load_env_key():
    # Prefer real env, then .env file
    k = os.environ.get("GOOGLE_PLACES_API_KEY")
    if k:
        return k
    for fn in (".env", ".env.local"):
        p = os.path.join(ROOT, fn)
        if os.path.exists(p):
            for line in open(p):
                m = re.match(r'\s*GOOGLE_PLACES_API_KEY\s*=\s*"?([^"\n]+)"?', line)
                if m:
                    return m.group(1).strip()
    return None

def gog(*args, timeout=60):
    env = dict(os.environ, GOG_ACCOUNT=ACCOUNT)
    try:
        return subprocess.run(["gog", *args], capture_output=True, text=True,
                              env=env, timeout=timeout).stdout
    except Exception as e:
        return ""

def fetch_lead_emails(maxn):
    out = gog("gmail", "messages", "search", 'subject:"New Call In Lead"',
              "--max", str(maxn), "--json", timeout=90)
    try:
        data = json.loads(out)
    except Exception:
        return []
    ids = [m["id"] for m in data.get("messages", [])]
    leads, seen = [], set()
    for mid in ids:
        body = gog("gmail", "get", mid, timeout=45)
        if not body:
            continue
        def grab(label):
            m = re.search(r'(?m)^' + re.escape(label) + r'\s*(.*)$', body)
            return m.group(1).strip() if m else ""
        business = grab("Business")
        cust = grab("Customer Name")
        phone = re.sub(r'\D', '', grab("Phone"))
        email_raw = grab("Email")
        email = ""
        if "@" in email_raw:
            em = re.search(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', email_raw)
            email = em.group(0) if em else ""
        comments = grab("Comments")
        zipc = re.sub(r'\D', '', grab("Zip"))[:5]
        crm = ""
        mc = re.search(r'CrmLeads/Details\?id=(\d+)', body)
        if mc:
            crm = mc.group(1)
        if business and (zipc or phone):
            key = (business.lower(), phone, zipc)
            if key in seen:
                continue
            seen.add(key)
            leads.append(dict(msg_id=mid, crm_id=crm, business=business,
                              customer=cust, phone=phone, email=email,
                              comments=comments, zip=zipc))
    return leads

def haversine(a, b, c, d):
    R = 3958.8
    p1, p2 = math.radians(a), math.radians(c)
    dp = math.radians(c - a); dl = math.radians(d - b)
    h = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return R * 2 * math.asin(math.sqrt(h))

def nearest_store(lat, lng, stores):
    best = min(stores, key=lambda s: haversine(lat, lng, s["latitude"], s["longitude"]))
    return best, round(haversine(lat, lng, best["latitude"], best["longitude"]), 1)

def map_category(business, comments, research):
    t = (research.get("type") or "").lower()
    types = " ".join(research.get("types") or []).lower()
    hay = f"{t} {types} {business.lower()} {(comments or '').lower()}"
    rules = [
        ("Mexican Restaurant", ["mexican"]),
        ("Restaurant", ["restaurant", "cafe", "bakery", "food", "pizza", "coffee", "bar", "grill", "diner"]),
        ("Auto Repair", ["car repair", "auto", "mechanic", "tire", "oil change", "speed, sound"]),
        ("Real Estate", ["real estate", "realtor", "realty", "broker", "coldwell", "windermere", "property buyers"]),
        ("Dentist", ["dentist", "dental", "teeth whitening", "orthodont"]),
        ("Beauty & Wellness", ["salon", "barber", "spa", "tattoo", "nails", "lash", "massage", "wellness"]),
        ("Home Services", ["landscaping", "cleaning", "construction", "contractor", "plumb", "electric", "charge", "house cleaning", "organizing", "roofing", "painting"]),
        ("Chiropractor", ["chiropract"]),
        ("Veterinarian", ["vet", "animal"]),
        ("Gym", ["gym", "fitness", "yoga", "playground"]),
        ("Childcare / Education", ["preschool", "daycare", "kids", "child", "school"]),
    ]
    for cat, kw in rules:
        if any(k in hay for k in kw):
            return cat
    return "Other"

def research_business(business, city, state, lat, lng, key, ctx):
    import urllib.request
    url = "https://places.googleapis.com/v1/places:searchText"
    body = json.dumps({
        "textQuery": f"{business} {city} {state}",
        "locationBias": {"circle": {"center": {"latitude": lat, "longitude": lng}, "radius": 40000.0}},
        "maxResultCount": 1,
    }).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("X-Goog-Api-Key", key)
    req.add_header("X-Goog-FieldMask",
                   "places.displayName,places.formattedAddress,places.primaryType,"
                   "places.primaryTypeDisplayName,places.types,places.rating,"
                   "places.userRatingCount,places.websiteUri,places.nationalPhoneNumber,places.id")
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
            res = json.loads(r.read())
        pl = (res.get("places") or [None])[0]
        if not pl:
            return {}
        return {
            "name": pl.get("displayName", {}).get("text"),
            "address": pl.get("formattedAddress"),
            "type": (pl.get("primaryTypeDisplayName", {}) or {}).get("text") or pl.get("primaryType"),
            "types": pl.get("types", []),
            "rating": pl.get("rating"),
            "reviews": pl.get("userRatingCount"),
            "website": pl.get("websiteUri"),
            "phone": pl.get("nationalPhoneNumber"),
            "place_id": pl.get("id"),
        }
    except Exception:
        return {}

def tier(cases):
    c = cases or 0
    return "LARGE" if c >= 30 else ("MEDIUM" if c >= 18 else "SMALL")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=80)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    summary = {"scanned": 0, "new": 0, "skipped_existing": 0, "researched": 0, "added": [], "errors": []}

    try:
        import pgeocode
    except ImportError:
        summary["errors"].append("pgeocode missing; run: pip3 install pgeocode --break-system-packages")
        print("RESULT:" + json.dumps(summary)); return

    live = json.load(open(HOT_LEADS))
    existing_crm = {x.get("crm_id") for x in live if x.get("crm_id")}
    existing_key = {(x.get("business_name", "").lower(), x.get("phone", ""), x.get("lead_zip", ""))
                    for x in live}
    stores = [s for s in json.load(open(STORES)) if s.get("latitude") and s.get("longitude")]

    leads = fetch_lead_emails(args.max)
    summary["scanned"] = len(leads)

    new_leads = []
    for l in leads:
        key = (l["business"].lower(), l["phone"], l["zip"])
        if (l["crm_id"] and l["crm_id"] in existing_crm) or key in existing_key:
            summary["skipped_existing"] += 1
            continue
        new_leads.append(l)
    summary["new"] = len(new_leads)

    if not new_leads:
        print("RESULT:" + json.dumps(summary)); return

    key = load_env_key()
    ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
    nomi = pgeocode.Nominatim("us")
    now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    records = []

    for l in new_leads:
        r = nomi.query_postal_code(l["zip"])
        if r is None or (isinstance(r["latitude"], float) and math.isnan(r["latitude"])):
            summary["errors"].append(f"zip miss: {l['business']} {l['zip']}")
            continue
        lat, lng = float(r["latitude"]), float(r["longitude"])
        city, state = str(r["place_name"]), str(r["state_code"])
        store, dist = nearest_store(lat, lng, stores)
        research = {}
        if key:
            research = research_business(l["business"], city, state, lat, lng, key, ctx)
            if research:
                summary["researched"] += 1
            time.sleep(0.3)
        cases = store["Case Count"]
        rec = {
            "store_id": store["StoreName"], "store_chain": store["GroceryChain"],
            "store_city": store["City"], "store_state": store["State"],
            "store_cycle": store["Cycle"], "store_cases": cases, "store_tier": tier(cases),
            "category": "Call-In Lead",
            "subcategory": map_category(l["business"], l["comments"], research),
            "business_name": l["business"], "contact_name": l["customer"],
            "rating": research.get("rating"), "reviews": research.get("reviews"),
            "address": research.get("address") or "", "phone": l["phone"],
            "email": l["email"], "_email": l["email"],
            "website": research.get("website") or "", "distance_mi": dist,
            "place_id": research.get("place_id"), "lat": None, "lon": None,
            "lead_zip": l["zip"], "lead_comments": l["comments"], "crm_id": l["crm_id"],
            "source": "Call-In Lead (email)", "status": "approved", "generated_at": now,
            "_research_match": research.get("name"),
            "_research_note": "" if research else "No Google listing found — use phone + zip; likely home/service-based",
            "_hook": f"Inbound call-in lead — {l['business']} contacted us directly. Comments: {l['comments'] or 'n/a'}",
            "_email_template_type": "initial",
            "_email_subject_template": "Following up on your call, {business}",
            "_email_body_template": (
                "Hi {contact},\n\nThanks for reaching out to IndoorMedia about {business}! "
                "You called in interested in advertising, and I'd love to help. We can get your "
                f"business in front of shoppers at the {store['GroceryChain']} in {store['City']} "
                "— the closest store to you.\n\nWhen's a good time for a quick 10-minute call to go "
                "over options and pricing?\n\nBest,\n{rep}\nIndoorMedia"),
        }
        records.append(rec)
        summary["added"].append(f"{l['business']} -> {store['StoreName']} ({dist}mi)")

    if records and not args.dry_run:
        bak = HOT_LEADS.replace(".json", f".backup-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.json")
        json.dump(live, open(bak, "w"), indent=2)
        live.extend(records)
        json.dump(live, open(HOT_LEADS, "w"), indent=2)
        summary["total_records"] = len(live)
        summary["backup"] = os.path.basename(bak)

    print("RESULT:" + json.dumps(summary))

if __name__ == "__main__":
    main()
