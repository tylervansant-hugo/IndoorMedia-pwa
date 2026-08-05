#!/usr/bin/env python3
"""
Scrape ad image + contact details from each source testimonial page and enrich
testimonials_slim.json so the Quote PDF can embed the actual ad + business
contact info locally (the source host sends NO CORS headers, so the browser
cannot fetch these at runtime).

For each record {id,u,...} in public/data/testimonials_slim.json this fetches
https://testimonials.indoormedia.com/<slug-from-u> and extracts the <dt>/<dd>
pairs (Grocery Store, Customer's Name, Business, Address, Phone) plus the ad
image path (/home/image/<id>-<slug>.jpg). The ad image is downloaded to
public/testimonial_ads/<id>.jpg and the record gains:

    img      -> "testimonial_ads/<id>.jpg"  (local, CORS-safe) or "" if none
    grocery  -> grocery store chain
    custname -> customer's name
    addr     -> business address
    phone    -> phone number

Usage:
  python3 scripts/scrape_testimonial_details.py            # all records
  python3 scripts/scrape_testimonial_details.py --limit 50 # first 50 (test)
  python3 scripts/scrape_testimonial_details.py --only 54592,54577
Resumable: skips records that already have img/phone unless --force.
"""
import json, os, re, html, sys, time, argparse
import urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SLIM = os.path.join(ROOT, "public", "data", "testimonials_slim.json")
ADDIR = os.path.join(ROOT, "public", "testimonial_ads")
BASE = "https://testimonials.indoormedia.com"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 IndoorMediaQuoteBot/1.0"


def clean(s):
    if not s:
        return ""
    s = s.replace("&#x9;", " ").replace("\t", " ")
    s = html.unescape(html.unescape(s))
    return re.sub(r"\s+", " ", s).strip()


def fetch(url, binary=False, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
    return data if binary else data.decode("utf-8", "replace")


DT_DD = re.compile(r"<dt[^>]*>(.*?)</dt>\s*<dd[^>]*>(.*?)</dd>", re.I | re.S)
IMG_RE = re.compile(r'/home/image/[^"\'>\s]+', re.I)


def parse_page(html_text):
    out = {"grocery": "", "custname": "", "addr": "", "phone": "", "img_path": ""}
    for mm in DT_DD.finditer(html_text):
        k, v = mm.group(1), mm.group(2)
        key = re.sub(r"<[^>]+>", "", k).strip().rstrip(":").lower()
        val = clean(re.sub(r"<[^>]+>", " ", v))
        if key.startswith("grocery"):
            out["grocery"] = val
        elif key.startswith("customer"):
            out["custname"] = val
        elif key == "address":
            out["addr"] = val
        elif key == "phone":
            out["phone"] = val
    m = IMG_RE.search(html_text)
    if m:
        out["img_path"] = m.group(0)
    return out


def slug_from_url(u):
    # https://testimonials.indoormedia.com/54592-reimun-... -> 54592-reimun-...
    return u.rstrip("/").split("/")[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--only", default="")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--sleep", type=float, default=0.15)
    args = ap.parse_args()

    os.makedirs(ADDIR, exist_ok=True)
    with open(SLIM) as f:
        records = json.load(f)
    if not isinstance(records, list):
        records = records.get("testimonials", [])

    only = set(x.strip() for x in args.only.split(",") if x.strip())
    todo = []
    for rec in records:
        rid = str(rec.get("id", ""))
        if only and rid not in only:
            continue
        if not args.force and rec.get("phone") is not None and rec.get("img") is not None:
            continue
        todo.append(rec)
        if args.limit and len(todo) >= args.limit:
            break

    print(f"Scraping {len(todo)} records (of {len(records)})...")
    ok = imgs = fail = 0
    for i, rec in enumerate(todo, 1):
        rid = str(rec.get("id", ""))
        u = rec.get("u", "")
        if not u:
            continue
        page_url = BASE + "/" + slug_from_url(u)
        try:
            page = fetch(page_url)
            d = parse_page(page)
            rec["grocery"] = d["grocery"]
            rec["custname"] = d["custname"]
            rec["addr"] = d["addr"]
            rec["phone"] = d["phone"]
            rec["img"] = ""
            if d["img_path"] and "logo" not in d["img_path"].lower():
                img_out = os.path.join(ADDIR, f"{rid}.jpg")
                if args.force or not os.path.exists(img_out):
                    try:
                        blob = fetch(BASE + d["img_path"], binary=True)
                        if blob[:2] == b"\xff\xd8":  # JPEG magic
                            with open(img_out, "wb") as g:
                                g.write(blob)
                            imgs += 1
                    except Exception as e:
                        print(f"  img fail {rid}: {e}")
                if os.path.exists(img_out):
                    rec["img"] = f"testimonial_ads/{rid}.jpg"
            ok += 1
        except urllib.error.HTTPError as e:
            rec.setdefault("img", "")
            rec.setdefault("phone", "")
            fail += 1
            print(f"  HTTP {e.code} {rid}")
        except Exception as e:
            rec.setdefault("img", "")
            rec.setdefault("phone", "")
            fail += 1
            print(f"  fail {rid}: {e}")
        if i % 50 == 0:
            print(f"  {i}/{len(todo)} ok={ok} imgs={imgs} fail={fail} — saving...")
            with open(SLIM, "w") as f:
                json.dump(records, f, ensure_ascii=False)
        time.sleep(args.sleep)

    with open(SLIM, "w") as f:
        json.dump(records, f, ensure_ascii=False)
    print(f"DONE. ok={ok} imgs={imgs} fail={fail}. Saved {SLIM}")


if __name__ == "__main__":
    main()
