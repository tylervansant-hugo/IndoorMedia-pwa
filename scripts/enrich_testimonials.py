#!/usr/bin/env python3
"""
Enrich IndoorMedia testimonials with derived category tags, normalized grocery
chain tokens, and city mentions for category-aware + hyper-local matching.

Input : public/data/testimonials_slim.json  (array of {b,c,id,u})
Output: public/data/testimonials_slim.json  (same array, each record ADDS
        biz, ch, cat, cities)
Backup: public/data/testimonials_slim.backup-<epoch>.json (created first)
"""
import json, os, re, html, sys, time, subprocess
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SLIM = os.path.join(ROOT, "public", "data", "testimonials_slim.json")
STORES = os.path.join(ROOT, "public", "data", "stores.json")

# ---------------------------------------------------------------------------
# Text cleaning
# ---------------------------------------------------------------------------
def clean(s):
    if not s:
        return ""
    s = s.replace("&#x9;", " ").replace("\t", " ")
    # decode HTML entities twice (some are double-encoded)
    s = html.unescape(html.unescape(s))
    return re.sub(r"\s+", " ", s).strip()

# ---------------------------------------------------------------------------
# Grocery chain normalization
# ---------------------------------------------------------------------------
def norm_chain(tok):
    """Normalize a raw chain token to a canonical lowercase key."""
    t = clean(tok).lower().strip()
    t = re.sub(r"[.,]+$", "", t).strip()
    aliases = {
        "frys": "fry", "fry's": "fry", "frys food": "fry", "fry": "fry",
        "food 4 less": "food4less", "food4less": "food4less",
        "stater bros": "stater bros", "stater bros.": "stater bros",
        "dillion stores": "dillon", "dillon stores": "dillon", "dillons": "dillon",
        "dillion": "dillon", "dillon": "dillon", "gerbes-dillon": "dillon",
        "king soopers": "king soopers", "smiths": "smiths", "smith's": "smiths",
        "fred meyer": "fred meyer", "qfc": "qfc",
        "quality food center": "qfc", "ralphs": "ralphs", "ralph's": "ralphs",
        "jewel-osco": "jewel", "jewel osco": "jewel", "jewel": "jewel",
        "vons": "vons", "von's": "vons", "pavilions": "pavilions",
        "shaws": "shaws", "shaw's": "shaws", "acme": "acme",
        "safeway": "safeway", "albertsons": "albertsons",
        "albertsons market": "albertsons", "kroger": "kroger",
        "bakers": "bakers", "baker's": "bakers",
    }
    if t in aliases:
        return aliases[t]
    # collapse trailing possessive s handled loosely later; keep as-is
    return t

def parse_chains(last_segment):
    out = []
    for part in re.split(r"[,/]| and ", last_segment):
        p = norm_chain(part)
        if p and p not in out:
            out.append(p)
    return out

# ---------------------------------------------------------------------------
# Category taxonomy — biz-name and comment keyword patterns.
# Vocabulary MUST match detectProspectCategories() in MeetingPrep.svelte.
# ---------------------------------------------------------------------------
# Each tag -> list of substrings (word-ish). Name matches weighted higher.
CATEGORY_PATTERNS = {
    "pizza":            ["pizza", "pizzeria", "pizzas", " pie ", "slice"],
    "mexican":          ["mexican", "taco", "tacos", "taqueria", "burrito", "cantina",
                         "enchilada", "carniceria", "tortilla", "el ", "los ", "las ",
                         "mariscos", "birria"],
    "sushi_japanese":   ["sushi", "japanese", "ramen", "teriyaki", "hibachi", "izakaya",
                         "sake", "poke"],
    "chinese":          ["chinese", "wok", "panda", "dim sum", "mandarin", "szechuan",
                         "hunan", "chow", "china "],
    "thai":             ["thai", "pad thai", "bangkok"],
    "indian":           ["indian", "tandoori", "masala", "naan", "curry hut", "biryani",
                         "punjab", "bombay", "himalayan", "tikka"],
    "bbq_burger":       ["burger", "bbq", "barbeque", "barbecue", "smokehouse", "grill house",
                         "wings", "wing ", "smoked", "brisket", "ribs"],
    "seafood":          ["seafood", "fish", "crab", "lobster", "oyster", "shrimp",
                         "fish & chips", "fish and chips"],
    "coffee":           ["coffee", "espresso", "roaster", "roasters", "tea house",
                         "cafe", "café", "coffeehouse", "latte", "brew coffee"],
    "bakery":           ["bakery", "donut", "doughnut", "pastry", "cake", "cupcake",
                         "bakeshop", "panaderia", "patisserie", "bagel"],
    "dessert":          ["ice cream", "frozen yogurt", "gelato", "creamery", "custard",
                         "smoothie", "shave ice", "froyo", "dessert", "chocolate",
                         "candy", "sweets", "wow cow"],
    "sandwich_deli":    ["sandwich", "sub ", "subs", "deli", "hoagie", "hoagies",
                         "cheesesteak", "delicatessen"],
    "bar_brewery":      ["bar ", " bar", "pub", "tavern", "taproom", "brewery", "brewing",
                         "brew ", "alehouse", "saloon", "lounge", "nightclub", "cocktail",
                         "wine bar", "barrel", "cantina", "sports bar", "grill & bar",
                         "bar & grill"],
    "restaurant":       ["restaurant", "diner", "bistro", "eatery", "kitchen", "grill",
                         "cuisine", "steakhouse", "steak house", "buffet", "cafe", "grille"],
    "salon_beauty":     ["salon", "hair ", "beauty", "lash", "brow", "blowout", "hair studio",
                         "hair design", "stylist", "waxing", "skincare", "esthetic"],
    "barber":           ["barber", "barbershop", "barber shop", "fades", "cuts"],
    "nails":            ["nail", "nails", "manicure", "pedicure"],
    "spa_massage":      ["massage", "spa", "wellness spa", "day spa", "reflexology",
                         "bodywork", "facial"],
    "auto_repair":      ["auto ", "automotive", "mechanic", "oil change", "brake",
                         "transmission", "car repair", "muffler", "smog", "collision",
                         "body shop", "lube", "auto repair", "engine"],
    "tires":            ["tire", "tires", "wheel", "wheels"],
    "car_wash":         ["car wash", "carwash", "detailing", "auto detail"],
    "dental":           ["dental", "dentist", "orthodont", "smile ", "teeth", "endodont",
                         "dds"],
    "medical":          ["medical", "clinic", "urgent care", "physician", "doctor",
                         "health center", "family practice", "pediatric", "dermatolog",
                         "optometry", "eye care", "vision center", "pharmacy"],
    "chiropractic":     ["chiropract", "chiro ", "spine"],
    "gym_fitness":      ["gym", "fitness", "crossfit", "yoga", "pilates", "training",
                         "athletic club", "martial arts", "jiu jitsu", "boxing", "cycle"],
    "vet_pet":          ["vet ", "veterinar", "pet ", "animal hospital", "grooming",
                         "pet store", "pet shop", "doggy", "kennel", "aquarium"],
    "insurance":        ["insurance", "allstate", "state farm", "farmers ins", "geico",
                         "agency"],
    "real_estate":      ["real estate", "realtor", "realty", "properties", "homes",
                         "brokerage"],
    "mortgage":         ["mortgage", "lending", "loans", "home loan", "escrow"],
    "cleaning":         ["cleaning", "maid", "janitorial", "housekeeping", "carpet clean",
                         "window clean"],
    "plumbing":         ["plumb", "plumbing", "drain", "rooter", "sewer"],
    "hvac":             ["hvac", "heating", "air condition", "furnace", "ac repair",
                         "cooling", "refrigeration"],
    "electrical":       ["electric", "electrician", "wiring", "lighting"],
    "roofing":          ["roof", "roofing", "gutter"],
    "landscaping":      ["landscap", "lawn", "tree service", "yard", "mowing", "nursery",
                         "garden center", "sprinkler", "irrigation"],
    "pest_control":     ["pest", "exterminat", "termite", "pest control"],
    "tax_accounting":   ["tax ", "taxes", "accounting", "cpa", "bookkeep", "payroll"],
    "florist":          ["florist", "floral", "flowers", "bouquet"],
    "jewelry":          ["jewelry", "jeweler", "jewelers", "diamond", "gold ", "watch"],
    "retail":           ["boutique", "supply co", "gift shop", "gifts", "furniture",
                         "mattress", "apparel", "clothing", "consignment", "thrift",
                         "hardware", "pharmacy"],
    "dry_cleaning":     ["dry clean", "dry-clean", "cleaners", "laundry", "laundromat"],
    "daycare_education":["daycare", "preschool", "learning center", "academy", "tutoring",
                         "child care", "childcare", "montessori", "school"],
    "legal":            ["law ", "lawyer", "attorney", "legal", "law firm", "law office"],
    "tattoo":           ["tattoo", "piercing", "ink "],
    "smoke_vape":       ["smoke shop", "vape", "vapor", "cigar", "tobacco", "hookah"],
    "cannabis":         ["cannabis", "dispensary", "marijuana", "weed ", "cbd"],
    "liquor_store":     ["liquor", "wine and spirits", "wine & spirits", "spirits",
                         "bottle shop", "package store", "wine shop"],
    "phone_repair":     ["phone repair", "cell phone", "iphone repair", "screen repair",
                         "device repair", "computer repair"],
    "home_services":    ["handyman", "remodel", "contractor", "construction", "flooring",
                         "painting", "fence", "garage door", "concrete", "paving",
                         "pool service", "home service"],
}

# Tags where a name-hit is a strong signal (food/business-name-y)
def categorize(biz, comment):
    biz_l = " " + biz.lower() + " "
    com_l = " " + comment.lower() + " "
    name_tags = set()
    all_tags = set()
    for tag, pats in CATEGORY_PATTERNS.items():
        for p in pats:
            if p in biz_l:
                name_tags.add(tag)
                all_tags.add(tag)
                break
        else:
            for p in pats:
                if p in com_l:
                    all_tags.add(tag)
                    break
    # If we matched a specific restaurant cuisine, also add generic restaurant
    cuisine = {"pizza", "mexican", "sushi_japanese", "chinese", "thai", "indian",
               "bbq_burger", "seafood", "sandwich_deli"}
    if all_tags & cuisine:
        all_tags.add("restaurant")
        if name_tags & cuisine:
            name_tags.add("restaurant")
    # Prefer name tags; if none, keep comment-derived tags but they're weaker.
    return name_tags, all_tags

# ---------------------------------------------------------------------------
# City detection
# ---------------------------------------------------------------------------
def load_city_index():
    stores = json.load(open(STORES))
    cities = set()
    for s in stores:
        c = (s.get("City") or "").strip()
        if len(c) >= 4:  # avoid tiny/ambiguous names
            cities.add(c.lower())
    # Drop city names that are common English words / too generic
    stop = {"union", "clinton", "franklin", "salem", "auburn", "madison", "milton",
            "aurora", "canton", "marion", "newton", "oxford", "dover", "troy",
            "buffalo", "orange", "sandwich", "surprise", "hobbs", "commerce",
            "riverside", "springfield", "columbia", "clayton", "arlington"}
    # keep them but require word boundary; only truly problematic short ones removed
    # Names that collide with common English words or appear inside other
    # words/phrases in testimonial comments (e.g. "social media", "black bear",
    # "dillon" the chain, "the market") -> too noisy to trust.
    hard_drop = {
        "surprise", "commerce", "orange", "sandwich", "hobbs", "media", "bear",
        "dillon", "lemoore" if False else None,  # keep lemoore
        "national", "liberty", "industry", "economy", "paradise", "security",
        "eagle", "buckeye", "christmas", "friendship", "enterprise", "reading",
        "mobile", "loving", "gardena" if False else None,
        "normal", "riverside", "lakeside", "hometown", "advance", "boring",
        "why", "blue", "comfort", "pride", "welcome", "needmore", "whitehall",
        "king", "forest", "pearl", "price", "spring", "springs", "grove",
        "valley", "hills", "heights", "park", "lake", "beach", "center",
        "village", "city", "plaza", "corner", "crossing", "station", "junction",
        "garden", "gardens", "meadows", "ridge", "summit", "harbor", "bay",
        "point", "landing", "crest", "woods", "creek", "falls", "cove",
        "downtown", "midtown", "uptown", "east", "west", "north", "south",
        "central", "main", "market", "receipt", "coupon", "program",
    }
    hard_drop = {x for x in hard_drop if x}
    cities = {c for c in cities if c not in hard_drop}
    return cities

def find_cities(comment, city_index, city_regexes):
    found = []
    low = comment.lower()
    for city, rx in city_regexes:
        if city in low and rx.search(low):
            found.append(city)
    return found

def main():
    if not os.path.exists(SLIM):
        print("Missing input", SLIM); sys.exit(1)

    # Backup first
    ts = int(time.time())
    backup = os.path.join(ROOT, "public", "data", f"testimonials_slim.backup-{ts}.json")
    subprocess.run(["cp", SLIM, backup], check=True)
    print(f"Backup -> {backup}")

    data = json.load(open(SLIM))
    print(f"Loaded {len(data)} records")

    city_index = load_city_index()
    print(f"City index: {len(city_index)} names")
    # Precompile word-boundary regexes only for multi-token / risky names lazily;
    # for speed, build a single alternation for whole-word membership check.
    city_regexes = [(c, re.compile(r"\b" + re.escape(c) + r"\b")) for c in city_index]

    cat_counter = Counter()
    n_cat = 0
    n_city = 0

    for rec in data:
        raw_b = rec.get("b", "")
        comment = clean(rec.get("c", ""))
        # parse segments
        segs = [clean(x) for x in raw_b.split(" - ")]
        segs = [s for s in segs if s]
        if len(segs) >= 3:
            biz = segs[1]
            chains_seg = segs[-1]
        elif len(segs) == 2:
            biz = segs[0]
            chains_seg = segs[-1]
        else:
            biz = segs[0] if segs else ""
            chains_seg = ""
        rec["biz"] = biz
        rec["ch"] = parse_chains(chains_seg)

        name_tags, all_tags = categorize(biz, comment)
        # cat = union, but ordered with name tags first
        ordered = list(name_tags) + [t for t in all_tags if t not in name_tags]
        rec["cat"] = ordered
        rec["catn"] = list(name_tags)  # matched on business NAME (strong)
        if ordered:
            n_cat += 1
            for t in ordered:
                cat_counter[t] += 1

        cities = find_cities(comment, city_index, city_regexes)
        rec["cities"] = cities
        if cities:
            n_city += 1

    # Write minified array
    with open(SLIM, "w") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))

    size_mb = os.path.getsize(SLIM) / 1e6
    print("=" * 50)
    print(f"Total records          : {len(data)}")
    print(f"With >=1 category      : {n_cat} ({100*n_cat/len(data):.1f}%)")
    print(f"With >=1 city mention  : {n_city} ({100*n_city/len(data):.1f}%)")
    print(f"Output size            : {size_mb:.2f} MB")
    print("Top categories:")
    for tag, cnt in cat_counter.most_common(25):
        print(f"  {tag:20s} {cnt}")

if __name__ == "__main__":
    main()
