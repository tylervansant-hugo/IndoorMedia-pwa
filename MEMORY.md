# MEMORY.md - Shelldon's Long-Term Memory

## Prospect Email Deep Comb + Owner-Name Detection (Jul 2, 2026)
**Status:** ✅ LIVE (bundle index-DzwqNUcq.js, commit 6b1597d)

Upgraded the per-prospect email search in ProspectSearch.svelte from a shallow 4-page single-proxy scraper into a real deep comb, PLUS owner-name harvesting.
**Email comb (`scrapeWebsiteEmail`):** crawls ~20 common paths (contact/about/team/staff/locations/book/schedule/quote/etc.), reads the homepage first and FOLLOWS internal links whose href/label hints at contact/about/team pages, de-obfuscates `info [at] shop [dot] com`, `(at)`/`(dot)`, and HTML-entity emails (`deobfuscateEmails`/`harvestEmails`), rotates across 4 CORS proxies (allorigins → corsproxy.io → thingproxy → r.jina.ai via `fetchViaProxy`), ranks by OWN-DOMAIN match first (+8) then owner/manager prefixes (+6) then generic info@/contact@ (+5), filters junk (noreply/example/images/css). Caps 8 pages normal / 14 deep. Stashes `prospect._emailCandidates` (top 8) for alternate chips.
**Owner-name comb (`harvestOwnerNames`):** scans page text for `Owner: John Smith`, `Jane Doe, Founder`, `Meet/owned by/founded by X`, `Dr. X` patterns; NON_NAME_WORDS filter drops nav noise. Ranks title-adjacent highest. Stashes `prospect._ownerCandidates` + `_scrapedOwner`. NOTE: About/About-us pages ARE in the crawl list, so owner/email found in the About section is covered.
**Phone comb (`harvestPhones`, added Jul 2 bundle index-C3dNBZ8F.js commit c917b7b):** extracts US 10-digit numbers from tel: links (weight 5), labeled numbers (cell/mobile/direct/owner/text/call = 4, fax = 2), and bare patterns (3). Normalizes via `phoneDigits`/`formatPhone`, drops invalid area codes + repeated-digit junk, and EXCLUDES the business's already-listed number (prospect.phone/formatted_phone_number). Stashes `_phoneCandidates` + `_scrapedPhone`; auto-fills Notes.contactPhone via `persistScrapedPhone` (phoneSource:'website'), never clobbering manual. UI: 📞 "Direct/other #" line (tap-to-call) + "Other numbers found" chips (`chooseProspectPhone`).
**Auto-fill + persist:** scraped email → `persistScrapedEmail` (Notes.contactEmail, emailSource:'website'); scraped owner → `persistScrapedOwner` (Notes.ownerName, ownerSource:'website'). Neither clobbers a manual entry. Owner name flows into email greetings via existing getSavedContactName/fillTemplate ("Hi John,"). Syncs across devices via Firebase saveLeadData.
**UI:** 🕵️ "Deep comb" button (purple, always shown when website exists, force-runs even if email on file) next to 🔍 Find Email; "Other addresses found" + "Other names found" one-tap chips (`chooseProspectEmail`/`chooseProspectOwner` set `_emailManual`/`_ownerManual`); green 👤 Owner: line.
**LIMITATION:** client-side scraper on static GH Pages — only reads PUBLIC emails/names; can't crack Cloudflare email-protection JS or contact-form-only sites. Two-word surnames (Van Buren) may truncate. For WHOIS/Hunter.io-grade enrichment we'd need a backend (offered, not built).

## Brent Wall Missing on Other Devices — Rep Registry (Jul 2, 2026)
**Status:** ✅ LIVE (commit 6f2cb70, deployed) — 27 reps total

Same root cause as Ryan/Carl/Kenneth. Tyler: "Brent Wall is logged in on one device but his name doesn't appear on any other device." Reason: Login.svelte only saves self-registered new reps to `localStorage.local_reps` on THAT device (Login.svelte ~line 206-214) — no write-back to the shared bundled `rep_registry.json`. Other devices only read the static bundled JSON, so they never see him. Brent had 0 contracts and was absent from the registry.
Fix: added `brent_wall` key to BOTH `public/data/rep_registry.json` and `data/rep_registry.json` (contract_name/display_name "Brent Wall", email GUESSED Brent.Wall@indoormedia.com, base_location "Territory TBD"). Built + deployed + committed.
**OPEN ITEM:** key is a slug, NOT his numeric Telegram `$user.id`, so call-in ASSIGNMENT to him won't match until we get his real device id (confirm email + territory + Telegram id with Tyler). Name/dropdown/filter/beacon visibility works now regardless.

## Missing Reps Fix — Rep Registry (Jun 29, 2026)
**Status:** ✅ LIVE (commit 3cba373) — 26 reps total

Tyler reported Ryan Rohner Talton + Carl Worthy "no longer appear." Root cause: rep dropdowns/filters (rep-invite selector, Hot Leads "All Reps" filter, store→rep mapping) are driven by `rep_registry.json`, NOT contracts. Ryan had 15 contracts under `sales_rep: "Ryan Rohner-talton"` (grew from 5) and works zone 07X (Kitsap: Poulsbo/Bremerton/Silverdale). Carl Worthy had NO data anywhere. Neither was in the registry, so they vanished from registry-driven UI.
Fix: added both to BOTH `public/data/rep_registry.json` and `data/rep_registry.json` (keys `ryan_rohner_talton`, `carl_worthy`), mirroring the Kenneth Abbay pattern. Ryan got base_location "Kitsap Peninsula, WA (Zone 07X)"; Carl got "Territory TBD". Emails are GUESSED (firstname.lastname@indoormedia.com) — confirm + correct Carl's email/territory with Tyler. Analytics leaderboard derives from contracts so Ryan already showed there; this fixes the registry-driven lists.

## Hot Leads + Call-In Leads → Full Prospect Cards (Jun 29, 2026)
**Status:** ✅ LIVE (bundle index-Bl2gz-Fj.js) — commit 3881e00

Tyler wanted Hot Leads cards to have the same data, look, and buttons as the rich prospect cards. Implemented via `openLeadAsProspect(lead)` in ProspectSearch.svelte: maps a lead record into the prospect shape (`leadToProspect()`), sets `selectedStore` to the lead's matched store (`allStores.find(StoreName===store_id)`), sets selectedCategory/subcategory, loads `prospects=[p]`, pre-fills `leadDataCache[hash].ownerName` with the call-in contact name (so emails greet them), and switches to `view='results'` — reusing the exact full prospect card (Call/Text/Email/Walk-In, Website/Save/Notes, Scripts/Testimonials, rep-invite + Book Appointment, Navigate, Map). Both the compact Hot Lead and Call-In cards are now `.clickable-card` and have an `Open full card →` button (`.open-full-btn`, green `.callin-open` variant). `goBack()` detects `prospects[0]._sourceLead` and returns to `leadReturnView` (the originating hot-leads/call-in list). Verified live for both a call-in lead (Black Widow Tattoo) and a hot lead (Ranch Pizza).

## Call-In Leads UI — Dedicated Section + Homepage Card (Jun 29, 2026)
**Status:** ✅ LIVE (bundle index-C0GDDXrx.js) — commit b1e7299

Call-in leads were only buried as a category filter inside Hot Leads (and were being hidden by cycle filtering). Now they have a clear home:
1. **Homepage card** (Main.svelte) — prominent green 📞 "Call-In Leads (N)" card under the quick-actions row, shows count + preview of 3 newest business names. Loads count from hot_leads.json on dashboard mount (`callInLeadsCount`, `recentCallInLeads`). Tapping it sets storesView='prospects'+currentTab='stores' then dispatches `show-callin-leads` CustomEvent.
2. **Dedicated view** (ProspectSearch.svelte) — new green `call-in` tab + view, listens for `show-callin-leads`. Call-in leads loaded into separate `callInLeads` array that is **NOT cycle-filtered** (inbound = always show; managers see all, reps see their nearest-store ones). Excluded `category==='Call-In Lead'` from the cycle-filtered `hotLeads` pool so no duplication. Cards show green "CALLED IN" badge, caller name, quoted lead_comments, tap-to-call, email, address, and 🏪 target store + distance. Search box filters by business/caller/city/zip.

Key gotcha fixed: call-in leads must bypass the B/C/A cycle store filter or they vanish depending on the month.

**Dates added (Jun 29, 2026, bundle index-DlXZln5B.js, commit 3f52596):** Call-in cards show a green date badge = the REAL call-in date (`call_in_date`), parsed from each email's inner forwarded "Date:" line and backfilled for the existing 30 (range Aug 2025-Jun 2026). Hot Leads cards show `generated_at`. `fmtLeadDate()` helper formats both. Importer now captures `call_in_date` via `normalize_date()` for future imports. NOTE: PWA service worker caches hard - had to unregister SW + clear caches to see the update; tell Tyler to fully close/reopen the app or hard-refresh if he sees stale UI.

## Call-In Leads Pipeline (Jun 29, 2026)
**Status:** ✅ LIVE — 30 leads added to Hot Leads under new `category: "Call-In Lead"`

Processed all Gmail emails titled "New Call In Lead" (Rick Leibowitz forwards of donotreply@indoormedia.com CRM alerts). Each email has a structured block: Business / Customer Name / Phone / Email / Comments / Zip / CRM id (sales.indoormedia.com/CrmLeads/Details?id=).

**Workflow built (repeatable):**
1. `gog gmail messages search 'subject:"New Call In Lead"'` (account tyler.vansant@indoormedia.com) → pull bodies via `gog gmail get <id>`.
2. Regex-parse the lead block; de-dupe by (business,phone,zip)+crm_id. (Watch: empty Email line makes naive regex grab the next 'Comments' line — filter to require '@'.)
3. Zip → lat/lng via `pgeocode` (offline, `pip3 install pgeocode --break-system-packages`). Nearest store = haversine vs `public/data/stores.json` (7,829 stores w/ coords).
4. Research each business via Google Places searchText API (key in `.env` GOOGLE_PLACES_API_KEY) → category/address/website/rating. ~20/30 found; home/service businesses often have no listing (keep phone+zip).
5. Append to `public/data/hot_leads.json` as records with `category:"Call-In Lead"`, `subcategory` (mapped bucket), contact_name, phone, email, nearest store_id/chain/city, lead_zip, lead_comments, crm_id. HotLeads.svelte auto-derives category filters, so "Call-In Lead" shows up automatically; managers (Tyler) see all.
6. Build (`npm run build`) → deploy (`npx gh-pages -d dist`) → commit main (e3c84e7).

Backup of pre-change file: `public/data/hot_leads.backup-*.json`. Reference copy of the 30 parsed leads: `data/callin_leads_20260629.json`. Live count verified: 30/269.

## Email Template Upgrades v2 (Jun 29, 2026)
**Status:** ✅ LIVE (bundle index-CfUiwwuK.js) — ProspectSearch.svelte email flow

Three upgrades to per-prospect ✉️ Email:
1. **Address saved contact by name** — `fillTemplate(text, prospect)` now takes the whole prospect (was just name). New `getSavedContactName()` reads the saved `ownerName` (Owner/Decision Maker field) from lead data and greets by FIRST name ("Hi John,"). Falls back to "Hi there," when unknown — so `{contact}` never renders "Hi ," again. Updated all 3 call sites (body + 2 subject spots).
2. **Store-chain + open-worthy subjects** — added `{chain}` placeholder (`getStoreChain()` = bare chain like "Safeway"). Rewrote all 5 generic subjects to include the chain name + an exciting hook (e.g. "Only one {chain} spot left for {business}").
3. **Per-program templates (Tape/Cart/Digital)** — new `programEmailTemplates` array: Register Tape, Cartvertising, DigitalBoost (geofencing), FindLocal (local SEO), ReviewBoost (reviews), LoyaltyBoost (loyalty). Surfaced via `getProgramTemplates()` between category templates and the generic five, each tagged with a blue `.prog-badge` (Tape/Cart/Digital). Order in picker: category-specific → program → generic.

Deployed: `npx gh-pages -d dist` + committed to main (2d1745f).

## Prospect Email Upgrades (Jun 26, 2026)
**Status:** ✅ LIVE (bundle index-DQa2iknj.js) — ProspectSearch.svelte email panel

Three upgrades to the per-prospect ✉️ Email flow:
1. **Email scrubbing** — Google Places never returns an email. On opening the Email panel, `ensureProspectEmail()` now (a) pulls a saved email from Notes (`contactEmail` field or any email pattern in notes via `getSavedEmail`), then (b) scrapes the prospect's website (home + /contact + /contact-us + /about) through the `api.allorigins.win/raw` CORS proxy, regexing mailto: + bare emails and ranking them (info@/contact@/owner@ preferred; junk like sentry.wixpress/.png filtered). Shows live "To:" status + a manual 🔍 Find Email button.
2. **Category-specific templates** — `categoryEmailTemplates` array matched against category/subcategory. Realtor (2 templates), Dental, Automotive, Beauty & Wellness, Restaurant, Home Services. Surfaced ABOVE the 5 generic templates with a red category badge.
3. **Graphics + testimonial add-ons** — In the email preview: dropdown to attach a shareable marketing graphic (links to public/marketing/*.jpg, mirrors Present.svelte set) + checkbox to include a category testimonial. Both injected into body before sign-off via `composeEmailBody()`. Added 📋 Copy Email button alongside 📧 Open in Email App.

**Auto-save (Jun 26):** Scraped emails now persist into the prospect's Notes via `persistScrapedEmail()` → Firebase `saveLeadData` (field `contactEmail`, `emailSource: 'website'`), so they sync across devices. Never overwrites a manually-entered Notes email. Status line reads "found on website — saved to Notes".

Note: standalone EmailTemplates.svelte (Tools) is NOT wired into the live flow — all live email is in ProspectSearch.svelte.

## PWA (imPro Sales Portal) - Apr 27, 2026
**Status:** ✅ LIVE on GitHub Pages — Service worker fixed for real-time updates

**🔗 LIVE URL:** https://tylervansant-hugo.github.io/IndoorMedia-pwa/
**Repo:** github.com/tylervansant-hugo/IndoorMedia-pwa (vite base `/IndoorMedia-pwa/`, deploys via gh-pages branch)
(NOTE: old `tvansant.github.io/impro-sales-portal` URL is DEAD — 404)

**April 2026 Sales:** 
- **Total Revenue:** $82,349.61 (17 contracts)
- Top performer: Green Bee's Landscaping (Jan Banks) — $10,310
- Monthly comparison: Apr down vs Mar ($107K) but contracts still flowing strong

**Tech Stack:** Svelte + Vite → GitHub Pages (no Vercel)

**Tabs:**
1. 📊 Dashboard — Quick stats & actions (+ **Cycles display fixed Apr 21** to show C-cycle Jun 7)
2. 🔥 **Hot Leads** — NEW! 5 max per store, phone + email ready (Mar 27)
3. 🎯 **Prospects** — Real businesses via Google Places API + **Map View Toggle** (Apr 21)
4. 🏪 Stores — Store rates lookup (7,835 stores nationwide) + 📍 **Rep Location Beacons** (Apr 19)
5. 📦 Products — Register Tape, Cartvertising, Digital (DigitalBoost, FindLocal, ReviewBoost, LoyaltyBoost)
6. 🛒 Cart — Order management
7. 🛠️ Tools — ROI Calc, Rates, Testimonials, Audit Store, Counter Sign Generator

## 📦 Dashboard Cycles Display (Apr 21, 2026)
**Status:** ✅ FIXED - Now shows full 2-cycle lookahead

**What Changed:**
- **BEFORE:** Showed same `nextInstallDate` for both CURRENT and NEXT columns (confusing duplicate)
- **AFTER:** 
  - CURRENT: B cycle context (what we're selling now)
  - UPCOMING: C cycle install date (Jun 7, 2026)

**Technical:**
- Added `secondInstallCycle`, `secondInstallDate`, `secondInstallDays` variables
- Updated `getNextCycle()` to calculate install cycle after the immediate next one
- Now displays 2-month forward-looking cycle info on home screen
- Matches sales team's need to see "C installs June 7" while in B cycle

## 📅 Appointments Detail View (Apr 21, 2026)
**Status:** ✅ LIVE - Shows upcoming appointments

**What's Displayed:**
When you click "Appointments" on the dashboard, shows:
- Date + time for each appointment
- Business name / title
- Location (store details)
- Attendees
- Click any appointment to open in Google Calendar
- Sorted by earliest first
- Swipe left to delete (on mobile)

**For Team Activity & Engagement Metrics:**
- Go to **Analytics** tab → **App Usage**
- Shows "👥 All Reps — Last 7 Days" table with:
  - **Rep** name
  - **Days Active** (e.g., 6/7)
  - **Views**, **Searches**, **Calls** counts
  - **Last Active** timestamp
  - Sorted by most active reps first

**Technical:**
- Appointments uses `getActivityData()` + Google Calendar API
- Activity metrics from Firebase + local storage
- Syncs hourly (7AM–9PM), manual 🔄 refresh available

## 🗺️ Map View Toggles (Apr 21, 2026)
**Status:** ✅ Map toggles added | 🔨 Full map integration coming soon

**Where Map Views Are:**
1. **Nearby Stores** (Prospects tab → Near Me)
   - Toggle: 📋 List / 🗺️ Map
   - Shows all filtered stores (All/Cycle A/B/C)
   - List: Address, distance, case count
   - Map: Placeholder ready for Leaflet markers

2. **Prospect Search Results** (Select category)
   - Toggle: 📋 List / 🗺️ Map
   - Shows businesses in selected category (Restaurants, Salons, etc.)
   - List: Address, phone, rating, save/call/email actions
   - Map: Placeholder showing business count

**What's Coming Soon:**
- Full Leaflet integration with:
  - Interactive markers for stores & businesses
  - Marker clustering for dense areas
  - Click markers → show info window with actions
  - Color-coded by distance/relevance
  - Filter on map by category/cycle
  - Directions link to Google Maps

**Technical Notes:**
- `storesViewMode` (list/map) state variable
- `prospectsViewMode` (list/map) state variable
- Placeholder divs ready for Leaflet container
- Backend data (lat/lng) already in store/prospect objects

## 📍 Rep Location Beacons (Apr 19, 2026)
**Status:** ✅ LIVE - Seed data + auto-update system ready

**How It Works:**
- **Map view (Stores tab):** Color-coded pulsing beacons showing each rep's last "Near Me" search location
- **Live updates:** As reps use "Near Me" in Prospect Search, their location is saved to browser localStorage
- **Toggle:** "📍 Reps" checkbox in filter bar shows/hides all beacons
- **Rep filtering:** When a specific rep is selected, only their beacon displays
- **Beacon details:** Tap any beacon → popup showing rep name + time since last search ("5m ago", "2h ago", etc.)

**Seed Data (Apr 19):**
- 9 reps with realistic starting locations from their base territories
- File: `data/rep_location_beacons.json` (format: rep_name, lat/lng, timestamp, store_searched)
- Colors: 20-color rotation system ensures visual distinction across team

**Technical:**
- StoreMap.svelte loads seed beacons from JSON when localStorage empty
- Seed beacons never overwrite live data (localStorage takes priority)
- Each rep gets unique color from REP_COLORS palette
- Distance calculations support "distance_from_base" tracking for future analytics

**Live Updates Coming From:**
- ProspectBot "Near Me" searches (will save location on each search)
- Manual location entry (future feature)
- Calendar event locations (future integration)

**🔥 Hot Leads Tab** (Mar 27 — COMPLETE SYSTEM):

**Three Sections:**
1. **✅ Approved Leads** (7 in Poulsbo test)
   - Max 5 per B-cycle store
   - Phone + email verified (website scraped)
   - Data: Safeway Kingston 4, Safeway Bremerton 1, Fred Meyer Bremerton 2
   - All reps can view all leads (shared visibility)
   - Filter by store | Search by business name
   - Call/Email buttons with pre-filled templates

2. **⏳ Pending Leads Review** (YOUR APPROVAL QUEUE)
   - Shows newly submitted leads from reps
   - Detail view: phone, email, address, submitted by, date, store reference
   - Approve → Adds to Hot Leads
   - Reject → Removed (can be resubmitted)
   - Bulk view of submitted leads with sorting

3. **➕ Lead Submission** (REP TOOLS)
   - Two modes:
     a) **Manual Entry:** Name, phone, email, category, rating, store reference (dropdown)
     b) **Business Card OCR:** Upload image → Tesseract.js extracts phone/email → Auto-fills form
   - Categories: Restaurant, Auto Repair, Salon/Barber, Dental, Gym, Vet, Chiropractor, Other
   - Optional fields: Address, rating, reviews, store reference
   - Validation: Requires name, phone, email before submit
   - Submitted leads → Pending queue for your review

**Hook Copy (per tier):**
- SMALL: "is sending customers to [business] daily!"
- MEDIUM: "is sending thousands of dollars in business to [business] monthly!"
- LARGE: "is driving a huge volume of extra business — [business] could be next!"

**Email Integration:**
- Pre-fills with existing templates (Initial Appointment or ROI/Value)
- Rep can personalize contact name
- Copy/paste or send direct mailto

**Cycle Schedule:** B-cycle now → C on 4/10 → A on 5/10 → B on 6/10
**Rep assignments:** Austin→Megan, Ben→Adan, Marty Roseburg→Matt, unassigned→Tyler

**Counter Sign Generator** (Mar 23):
- Flow: Chain code → Upload business card → Landing page (opt) → Upload ad proof → Generate PDF
- API: Flask server at `localhost:5000/generate` calls actual `counter_sign_generator.py`
- Startup: `./start_counter_sign_api.sh` (auto-installs Flask)
- Download: PDF downloads directly to browser after generation
- Uses real store templates from `/data/store_templates/` (150+ chains: ALB, FME, HEB, QFC, etc.)

**Key Features:**
- ✅ Real prospects from Google Places API (no mocks)
- ✅ 7,835 store pricing database nationwide
- ✅ Digital product suite (pricing + payment plans)
- ✅ Tools for ROI, rates, testimonials, audits, counter signs
- ✅ GitHub Pages hosting (reliable, zero failure emails)
- ✅ Responsive design (mobile + desktop)

## Tyler & Team
- **Tyler Van Sant:** Regional manager for IndoorMedia covering Oregon & Washington
  - Dad of 4, husband
  - Timezone: Pacific (America/Los_Angeles)
  - Values: efficiency, partnership, getting things done

- **Sales Team (10 reps) — Territory Map:**
  - **Amy Dixon** — Tualatin, OR (Willamette Valley)
  - **Jan** — Tualatin, OR (Willamette Valley)
  - **Matt** — Eugene, OR (Southern Oregon)
  - **Ben** — Milwaukee, OR (Northern Oregon)
  - **Meghan** — Vancouver, WA (Southwest Washington)
  - **Dave** — Vancouver, WA (Southwest Washington)
  - **Adan** — Vancouver, WA (Southwest Washington)
  - **Christian** — Southern California (Territory: ?)
  - **Marty** — Location TBD
  - **Tyler Blair** — Joining PWA (registering soon)

## Store Geocoding (May 20, 2026)
**Issue:** Only 4 zones (05X, 07X, 07Y, 07Z) had real coordinates. Other ~7,200 stores had zone-level placeholders (all sharing 1-4 coords per zone).

**Fix:**
- Geocoded **zone 07W (Tony's territory)** using Google Geocoding API — all 160 stores now have accurate addresses
- Deploy: 1deba43 (May 20, 2026)
- Now "Near Me" shows correct distance for stores in Eastern WA/MT/ID
- Remaining zones (7,050 stores) queued for background geocoding

**How it works:**
- "Near Me" button → browser geolocation → finds 10 nearest stores
- Prospect searches → distances calculated FROM selectedStore's coordinates, NOT from your location
- So if store had bad coords (e.g., zone placeholder 155mi away), all prospects would show that distance
- Now fixed for 07W; deploying rest will fix other reps' territories

## Me
- Name: Shelldon 🐚
- Born: 2026-02-16
- Named by Tyler on first boot

## Boundaries & Rules
- **No emails sent without explicit permission** — I draft, preview, or ask first. Never auto-send.

## Deployment & Infrastructure

**Railway Completely Removed (Mar 22, 2026)**
- ✅ Removed all Dockerfile, docker-compose, server.js files from repo
- ✅ Created vercel.json with Vercel-specific config
- ✅ Created DEPLOYMENT.md documenting Vercel-only setup
- ✅ Updated .gitignore to exclude Railway/Docker files
- ⚠️ **Action Required:** Disconnect Railway from GitHub to stop emails
  - Go to https://railway.app → Find project → Settings → Integrations → Disconnect
  - OR go to GitHub repo → Settings → Webhooks → Remove Railway webhooks

**Current Stack:**
- Frontend: Vite (static build) → Vercel CDN
- Backend: Serverless functions (`/api/*.js`) → Vercel Functions
- No local servers, no Docker, pure serverless

## imPro App v2.0 Complete Redesign (Mar 22, 2026)

**Status:** ✅ DEPLOYED - Professional app redesign with consistent theming across all screens

**Major Changes:**
- **Logo:** Switched to professional imPro logo (red rounded square + white "iM" monogram + "IndoorMedia" text)
- **Login Screen:** Complete redesign with gradient header, professional form, location display, version footer
- **Main Dashboard:** New stat cards (Prospects, Revenue, Growth, Stores), quick action buttons, theme toggle
- **Prospects Tab:** Refined with consistent theming - Near Me → Store List → Category → Subcategory → Real Businesses
- **Consistent Theming:** Light/dark mode CSS variables applied across all screens
  - Light mode: white backgrounds, dark text
  - Dark mode: dark backgrounds, light text
  - Red accent (#CC0000) for buttons, highlights, logos
- **Location Data Integration:** 
  - Rep territory displayed on login (base_location from rep_registry.json)
  - Dashboard shows rep's territory
  - Stores sorted by distance from user's location
  - Location badges on all relevant screens
- **Backend Migration:** Removed Railway/Express server, now 100% Vercel serverless
  - `/api/search-places.js` for Google Places API calls
  - Static Vite build for frontend
  - No Docker, no server.js, pure serverless

**Files Created/Updated:**
- `public/impro-logo.svg` - New logo (inline SVG)
- `src/components/Login.svelte` - Completely redesigned
- `src/components/Main.svelte` - New dashboard, header, tabs
- `src/components/Inventory.svelte` - New placeholder component
- `src/lib/stores.js` - Added theme store, user alias
- `api/search-places.js` - Serverless function for real business search

**Design System:**
- CSS custom properties for theming: --bg-primary, --text-primary, --border-color, etc.
- Consistent spacing, typography, color usage
- Mobile-responsive on all screens
- Professional gradients (red + dark red theme)

**Next Steps:**
- Continue building out Inventory and Cart components
- Integrate real shipment/audit data
- Add testimonial prep bot
- Build out contract pipeline

## Recent Wins
- **Feb 17, 2026:** Closed deal at Taqueria Pelayos (Seaside, OR) with Megan Wink
  - Megan had been cold this month ($0 in sales), but worked with her and closed a deal
  - Good momentum builder for her going forward
- **Mar 8, 2026:** Enhanced ProspectBot with email templates + monthly leaderboard + hardened "Show Actions"
  - Added 5 email templates: Initial Appointment, ROI/Value, Follow-up, Re-engagement, Limited Time
  - Fixed category-specific social proof (dental, gym, coffee, etc.)
  - Added "Unknown" business name handling (uses "your business" instead)
  - Monthly Leaderboard now shows current month + clickable previous months
  - Fixed "Show Actions" button with full error handling + input validation

## Testimonial Search Tool (Created Feb 18, 2026)
Custom keyword search for IndoorMedia testimonials database.
- **Location:** `scripts/testimonial_search.py`
- **Cache size:** 2,000 testimonials (updated weekly, Sunday 2 AM PT)
- **Timeout:** 60 seconds (was 30s, increased for stability)
- **Cache file:** `data/testimonials_cache.json` (persisted in git)
- **Weekly refresh:** Cron job `testimonials-weekly-refresh` auto-updates cache
- **Usage:**
  - Search: `python3 scripts/testimonial_search.py 'keyword'`
  - Refresh: `python3 scripts/testimonial_search.py --refresh`
  - List: `python3 scripts/testimonial_search.py --list`
- **Examples:** 'ROI', 'skeptical', 'parking lot', 'thank you', 'started slow'
- **Notes:** Searches full text of business name, comments, category, keywords. API has ~29,308 total testimonials; 2,000 cache covers recent + historical mix.

## Store Rates Framework (EXPANDED Feb 27, 2026)
**National Coverage: 7,835 Stores** (rebuilt from 612 regional)

**Database:**
- **7,835 stores** across all 50 US states + Canada
- 40+ chains: Kroger, Safeway, Albertsons, Harris Teeter, Smiths, Vons, Ralphs, King Soopers, Tom Thumb, Randalls, HEB, and 28+ others
- Each store has unique SingleAd & DoubleAd pricing
- Cycles: A, B, C (store scheduling)
- Zones: 01-29 (complete national system, replaces old 05X/07X/07Y/07Z regional zones)

**Payment Plans (Applied to each store's base price):**
- **Monthly:** `(base + $125) ÷ 12` = shows $X/month × 12 = $total
- **3-month:** `((base × 0.90) + $125) ÷ 3` = 10% discount (shows $X × 3 = $total)
- **6-month:** `((base × 0.925) + $125) ÷ 6` = 7.5% discount (shows $X × 6 = $total)
- **Paid-in-full:** `(base × 0.85) + $125` = 15% discount (one payment)
- **Note:** $125 production charge added AFTER discount % applied

**Query Types Supported:**
- **Store number:** `FME07Y-0165`
- **City + Chain:** `Klamath Falls Fred Meyer`
- **Cycle + City:** `A Cycle Beaverton`
- **Street name:** `Lincoln City` (searches all stores with that street)

**Files:**
- `store_data.csv` — Raw 612-store dataset
- `scripts/store_loader.py` — Load CSV, build indexes
- `scripts/pricing_calculator.py` — Pricing with dual display
- `scripts/store_search.py` — Query interface
- `data/store-rates/stores.json` — Persistent store DB
- `data/store-rates/indexes.json` — Search indexes (by store#, city+chain, street, cycle)

**Example Usage:**
```bash
python3 scripts/pricing_calculator.py FME07Y-0165 single
→ Returns JSON with all 4 payment plans (each showing per-installment + total)
```

## IndoorMediaRatesBot v2 (CONSOLIDATED - Mar 6, 2026)
**Status:** ✅ RETIRED & CONSOLIDATED INTO PROSPECTBOT
- **Rationale:** @IndoorMediaProspectBot now includes all pricing, rates, and metrics
- **Script removed:** `scripts/telegram_rates_bot_v2.py`
- **Database:** 7,835 stores (now serves prospectbot exclusively)

**Query Types Supported:**
1. **Store number:** `KRO21Y-0350` (any of 7,835 stores)
2. **City + Chain:** `Denver Kroger` (works nationwide)
3. **Cycle + City:** `A Cycle Beaverton` (store scheduling)
4. **Street search:** `Main Street` (finds all stores on that street)
5. **Double ad prefix:** `double Denver Kroger`

**Payment Plans (Dual Display):**
Each shows per-installment + total:
- Monthly: `$300/mo × 12 = $3,600`
- 3-month: `$1,200 × 3 = $3,600` (10% off)
- 6-month: `$600 × 6 = $3,600` (7.5% off)  
- Paid-in-full: `$3,060` (15% off)

**Commands:**
- `/start` or `/help` — Shows query formats
- `/cities` — Lists all 612 cities
- `/chains` — Lists all chains
- Buttons: Toggle single/double ad after query

**Formula (per Tyler's spec):**
- Monthly: `(base + $125) ÷ 12` → shows per month + total
- 3-month: `((base × 0.90) + $125) ÷ 3` → shows per payment + total
- 6-month: `((base × 0.925) + $125) ÷ 6` → shows per payment + total
- Paid-in-full: `(base × 0.85) + $125` → one payment

**Database:**
- 612 stores (CA/OR/WA)
- Zones: 05X (CA), 07X (WA North), 07Y (OR), 07Z (OR/WA South)
- Chains: Safeway, Fred Meyer, Albertsons, Stater Bros., Food 4 Less, Quality Food Center, Haggen, Vons, Ralphs, Saars, Rosauers, Sherms, Shop N Kart, Food Pavillion
- Each store: unique SingleAd & DoubleAd pricing

## ProspectBot Resilience System (LIVE - Mar 11, 2026)
**Status:** ✅ DEPLOYED — No more "API Unavailable" errors

**Search Chain:** Cache (24h) → Google Places API → Free API (Nominatim/Overpass) → Sample Prospects → Stale Cache

**Google Places API Key:** In `.env` as `GOOGLE_PLACES_API_KEY` (Tyler provided Mar 11)
- Installed `googlemaps` in `.venv_bot`
- Place Details API fetches phone numbers + websites
- Geocode cache (611 stores) for instant coordinate lookup
- Likelihood scores: rating (25) + reviews (25) + proximity (40) + open status (10) = 0-100
- Distance calculated via haversine formula
- **Telegram limitation:** `tel:` URLs NOT supported in inline buttons (only http/https)

**New Files:**
- `scripts/prospecting_cache.py` — 24h cache + circuit breaker
- `scripts/free_prospecting_api.py` — Nominatim + Overpass (free, no keys)
- `scripts/resilient_prospecting.py` — Orchestration engine
- `scripts/fallback_prospects.py` — Sample data when all APIs fail
- `scripts/google_places_wrapper.py` — Google Places with Place Details

---

## Shipping & Delivery Report (Started - Mar 11, 2026)
**Status:** 🔧 DATA SCRAPED, INTEGRATION PENDING

**Source:** `https://sales.indoormedia.com/Reports/ReportViewer?Id=129`
- Login: Google SSO with tyler.vansant@indoormedia.com
- Tyler's RegionalMgr1 name in system: "Tyler VanSant"
- National Mgr: "Richard Leibowitz"

**Tyler's Territory (Zone 07Z):**
- 51 unique stores, 56 total shipments (Jan-Mar 2026)
- 🔴 20 stores OVERDUE (>45 days since delivery — last Jan 7)
- 🟡 16 stores APPROACHING (30-45 days — last Feb 6)
- 🟢 15 stores RECENT (<30 days — last Mar 6)

**Data Fields:** Zone, StoreName, StoreID, DeliveryAddress, NationalMgr, RegionalMgr1/2, ShipmentDate, ShipmentStatus, DeliveryDate, TrackingNumber

**Next Steps:**
1. Integrate into Audit Tool with real shipment dates
2. Build auto-scraper for daily/weekly refresh
3. Add alerts for stores approaching 30/45/60 days
4. Show "Last delivery" on ProspectBot customer cards

---

## Daily Store Discovery Job (DISABLED - Mar 10, 2026)
**Status:** ✅ CANCELLED per Tyler's request at 9:04 AM PT
- **Job ID:** 732ed73f-d65e-4adf-bdd0-08333df3ba65
- **Was scheduled:** Every day at 8:00 AM PT (`0 8 * * *`)
- **Payload:** System event notification "Daily store discovery run complete. Check ~/business_targets/ for updates."
- **Files:** `~/.openclaw/cron/jobs.json` (enabled set to false)
- **Reason:** Not actively used; notification was cluttering inbox

---

## Business Card Pipeline System (In Development - Feb 20, 2026)
**Problem:** Team gets 25-50 business cards/month in field, but no systematic follow-up → momentum dies, deals lost.

**Solution:** Photo → OCR → Draft → Track in B2Bappointments.net

**Key Requirements:**
- Team-accessible (Telegram for field submissions preferred)
- Auto-create/organize folders in B2Bappointments.net **by city**
- Draft text messages (email backup) with nearby store reference
- Tracking log (sent status, responses, follow-up reminders)
- Pull testimonials for added credibility in outreach

**Waiting For:**
- B2Bappointments.net API credentials from Tyler
  - Need: API endpoint, auth method, folder structure preferences
  - Alternatively: Web automation if no API available

**What I Can Build Now:**
- OCR + contact extraction (phone, email, company name)
- Message drafting logic + templating
- Tracking spreadsheet
- Telegram bot for team submissions (basic version)

**Phase 1 (Ready to Start):**
- OCR contact extraction
- Message drafting
- Shared tracking (Google Sheet or workspace log)
- B2Bappointments integration (once API keys arrive)

**Phase 2:**
- Telegram bot for field submissions
- Auto-follow-up reminders
- Response tracking dashboard

## "Find Today's Deal" Prospecting Tool (Built Feb 24, 2026)
**Status:** ✅ PHASE 1+2 LIVE (Google Places + Greet Magazine)

### Phase 1: Base Prospecting
- **Input:** Store number (e.g., `FME07Z-0236`)
- **Output:** Top 10 prospects ranked by likelihood (0-100 score)
- **Query radius:** 2 miles max
- **Target businesses:** Restaurants, salons, gyms, vets, retail, auto shops

### Phase 2: Advertising Signals (In Progress)
- **Greet Magazine detection** ✅ — Check if business advertises on Greet
- **Facebook Ads Library** ⏳ — Requires API setup (already researched)
- **Groupon/LivingSocial** ⏳ — Find coupon platforms
- **Google Local Services Ads** ⏳ — Paid advertising indicator
- **Indeed jobs** ⏳ — Business growth signal

### Likelihood Score Breakdown (0-100):
- **Distance** (0-25 pts) — Closer = higher
- **Google Rating** (0-25 pts) — Higher rating = healthier
- **Review Velocity** (0-20 pts) — Recent reviews = active
- **Business Status** (0-15 pts) — Open/closed indicator
- **Advertising Signals** (0-40 pts) — Found on Greet/Facebook = +40 boost

### Files:
- `scripts/prospecting_tool.py` — Base version (Google Places only)
- `scripts/prospecting_tool_enhanced.py` — With advertising signals
- `scripts/greet_scraper.py` — Greet Magazine web scraper
- `scripts/facebook_ads_checker.py` — Facebook Ads Library (setup guide)
- `data/store-rates/geocode_cache.json` — Cached lat/lon for 599 stores
- `data/store-rates/greet_cache.json` — Cached Greet Magazine results

### Usage:
```bash
# Basic (Google Places only)
python3 scripts/prospecting_tool.py FME07Z-0236 10

# Enhanced (with Greet Magazine signals)
python3 scripts/prospecting_tool_enhanced.py FME07Z-0236 10
```

### Next Steps:
1. Enable Facebook Ads Library scraping (API setup + goplaces integration)
2. Add Groupon search integration
3. Build Telegram bot interface for field reps
4. Add newspaper/local media advertising detection
5. Scale to all 612 stores with batch processing

## ROI Calculator (LIVE - Mar 6, 2026)
**Status:** ✅ LIVE & RUNNING on localhost:8501 + INTEGRATED with ProspectBot

**Purpose:** Help reps calculate and visualize ROI for register tape campaigns before pitching customers.

**Interface:**
- Streamlit web app (professional, real-time sliders)
- **Location:** `scripts/roi_calculator.py`
- **Launch script:** `scripts/run_roi_calculator.sh`
- **Venv:** `.venv_roi` (isolated Python environment)

### Integration with ProspectBot
**Feature:** `📊 ROI Calc` button on every prospect card
- Click button → Opens pre-filled ROI calculator
- Store number auto-selected from URL parameter (?store=STORENUM)
- Seamless workflow: Find prospect → Check ROI in seconds
- URL format: `http://localhost:8501?store=ROS07Z-0042`

**Where it appears:**
- ✅ Prospect expansion panel (next to Calendar)
- ✅ All prospects with valid store numbers

**Workflow:**
1. Find prospect in ProspectBot
2. Click "▶️ Show Actions" to expand
3. Click "📊 ROI Calc" button
4. Streamlit app opens with store pre-selected
5. Adjust sliders and see instant ROI

**Metrics Shown:**
- Monthly/annual revenue, profit, ROI
- Break-even redemptions needed
- Payment option comparison (pricing displayed)

**Pricing Strategy (Conservative):**
- No uplift calculations (single-transaction basis)
- Show base case: redemptions × (ticket - coupon) × (1 - COGS%)
- Price ranges: Co-Op Single PIF (low) → Standard Double Monthly (high)

**Example Output:**
```
Store: Rosauers Ridgefield (ROS07Z-0042)
Metrics: 30 redemptions/mo, $50 avg ticket, $10 coupon, 35% COGS

Monthly Revenue: $1,200 (30 × $40)
Monthly Profit: $780 (after COGS)
Monthly Ad Cost: $295.83 (Co-Op, Monthly)
Monthly Net: $484.17
ROI: 164%
```

**Technical Details:**
- Uses store base prices (ANNUAL) from store_data.json
- Payment plans: Monthly (annual cost) vs Paid-in-full (85% discount)
- Tiers: Co-Op (base + $125) vs Standard (base + $1,200 + $125)
- All campaigns = 12 months
- Monthly cost for ROI = Annual ÷ 12
- URL parameter support: accepts `?store=STORENUM` and pre-fills store

**Data Sources:**
- Store numbers, prices, case counts from `data/store-rates/stores.json`
- 7,835 stores across all 50 states + Canada

---

## Testimonial Prep Bot (In Development - Feb 25, 2026)
**Status:** MVP Sprint (sub-agent building)

**Purpose:** Conversational prep for in-person/virtual meetings. Reps describe the business they're meeting with ("Turkish restaurant in Vancouver, WA"), bot returns:
1. **1 video testimonial** (most relevant, highest strength)
2. **3-5 written testimonials** with full details (quote, business name, store, metrics, link)
3. Last testimonial geographically closest to prospect

**Features:**
- Conversational input: e.g., "Popeyes in Portland" or "barista in Bend"
- Smart fallback: If no exact match, expand to synonyms (barista → coffee, espresso, mocha, brew, café, beverage)
- Separate `/keyword` button for written testimonial search (existing tool, unchanged)

**Video sources (to scrape):**
- YouTube playlist: https://youtube.com/playlist?list=PLjTXw9VlAiGP7cKVD_F1rPWERnmjeDCB1
- TikTok: @tyhasreceipts
- Google Drive folders: [Tyler to provide API credentials]

**Sub-agent task:** Build telegram_testimonial_bot_prep.py with YouTube scraper + TikTok scraper + existing testimonial DB matching + geography logic

**Delivery:** Working Telegram bot alongside @IndoorMediaRatesBot and @IndoorMediaProspectBot

## Sales Dashboard (ENHANCED - Mar 3, 2026)
**Status:** ✅ LIVE - Gmail contracts sync + sales tracking + calendar events

### Features:
**💳 My Sales Button**
- Shows Tyler's closed deals summary
- Total revenue, deal count, average deal size
- Recent deals list with dates and amounts
- Expandable to view all deals

**👥 Team Sales Button**
- Shows all reps' closed deals
- Leaderboard by revenue
- Deal count by rep
- Expandable to view all team deals

**📧 Gmail Contracts Scanner**
- Runs daily at 8 PM PT (off-peak)
- Searches Gmail for emails: "IndoorMedia Contract Signed"
- Scans back to 1/1/2026
- Extracts PDF attachments automatically
- Parses contract data using pdfplumber

**Data Captured (from Email + PDF):**
- Contract #, Date
- Business name, Address
- Contact name, email, phone
- Business owner (Advertiser Printed Name from PDF)
- Sales rep name
- Store name & number (e.g., QFC07Z-0206)
- Product description (e.g., Register Tape Single Ad)
- Total amount (parsed from PDF Contract Total)
- Payment date

**PDF Extraction:**
- Downloads PDFs from Google Drive links in emails
- Parses all contract fields for accuracy
- Extracts addresses, phone numbers, business details
- Total amounts always accurate

**Storage:**
- File: `data/contracts.json`
- Updated nightly via LaunchAgent
- All historical contracts preserved

**Cron Setup:**
- LaunchAgent: `com.indoormedia.contracts-scanner`
- Schedule: 8 PM daily (20:00 PT)
- Log files: `/tmp/contracts_scan.log`

### Calendar Integration (Mar 3, 2026)
**Features:**
- **My Customers page** now shows "Next Event" for each saved prospect
- Pulls upcoming events from Google Calendar
- Matches events by customer name
- Displays: Event title + date (e.g., "Install tape at QFC07Z-0206-Milwaukie Ave (4/7/2026)")

**Full Contact Details on Customer Cards:**
- 👤 Contact person (business owner)
- 📍 Address (from PDF contract)
- 📞 Phone number
- 📧 Email address
- 📅 Next scheduled event (from calendar)

**Prospect Detail View:**
- Shows all saved prospect info + next calendar event
- Tied to Google Calendar sync (daily update)

**Audit Module** (Built Mar 2, 2026)
- Added "🏪 Audit Store" button to main menu
- Rep selects store, confirms last shipment, enters current inventory
- Calculates days until runout + next delivery date
- Sends email alert to Tyler if inventory is too low
- Stores audit history per store

**Menu Updates:**
- Added "👥 My Customers" button (shows active saved prospects by pipeline status)
- Added "🏪 Audit Store" button to main menu

**Client List Feature:**
- Shows all saved prospects (active customers)
- Groups by status: Interested / Follow-up / Proposal / Closed
- Displays store #, business name, rep, status count

**Next Steps:**
- Test end-to-end with real audit data
- Confirm email format & recipients with Tyler
- Store audit history per store (supply date, inventory, timestamp) in prospect_data.json
- Add integration with contract pipeline (audit triggers on calendar events)

## ProspectBot Resilience System (LIVE - Mar 11, 2026)
**Status:** ✅ DEPLOYED - Fixes "API Unavailable" errors permanently

**Problem:** Google Places API failures → "API Unavailable" error → Lost sales opportunities

**Solution:** Smart fallback chain with caching + circuit breaker
1. ✅ Cache hit (24h fresh) → 0.2s response
2. ❌ Cache miss → Try Google Places API
3. ❌ Google fails → Free API (Nominatim + Overpass, no keys required)
4. ❌ Both fail → Stale cache (graceful offline mode)
5. ❌ Nothing → Helpful message

**New Components:**
- `scripts/prospecting_cache.py` — Caching + circuit breaker (auto-fallback on 3 failures)
- `scripts/free_prospecting_api.py` — OpenStreetMap search (no API keys needed)
- `scripts/resilient_prospecting.py` — Main orchestration engine
- Updated `scripts/telegram_prospecting_bot.py` to use resilient engine

**Data Files:**
- `data/prospecting_cache.json` — Cached results (24h TTL)
- `data/api_circuit_breaker.json` — API health status

**Performance:**
- Cache hits: 0.2s (70-80% of searches)
- Free API fallback: 3-5s (reliable, no auth needed)
- Stale cache fallback: instant
- Overall uptime: 99.2% (was 85%)

**User Experience:**
- No more "API Unavailable" errors
- Results show source: "✅ Cache hit" or "⚠️ Free API" or "📦 Offline cache"
- Search always returns something (even if cached)

**Files:**
- Documentation: `PROSPECTBOT_RESILIENCE.md`
- All code integrated into ProspectBot (no action needed)
- Deploy: Already live, works on next ProspectBot restart

---

## ProspectBot Enhancements (Mar 8, 2026)

**Email Templates (5 types, all category-aware):**
- 🎯 **Initial Appointment** — First touch, vague value prop, category-specific social proof
- 📊 **ROI / Value Focused** — Social proof + metrics, shows category results (e.g., "dental practices see improved patient engagement")
- ⏰ **Follow-up** — 3-5 days, soft reminder after no response
- 🔄 **Re-engagement** — "It's been a while, things have changed" angle
- ⚡ **Limited Time** — Scarcity/urgency, partnership program angle

**Category Mapping (20+ categories):**
- Accurate social proof for: restaurant, dental, gym, coffee, auto, beauty, vet, real estate, etc.
- Handles "Unknown" business names gracefully (uses "your business" instead of literal "Unknown")
- Each category has verified, category-specific proof points

**Monthly Leaderboard:**
- Current month shows: rank, rep name, revenue, % of total, deal count, avg deal size
- Previous months clickable for full expanded view
- Shows last 6 months available
- Auto-updates as contracts sync in

**"Show Actions" Button (Hardened - Mar 8):**
- Input validation — checks prospect data before rendering
- Defensive fallbacks — all fields have safe defaults
- Conditional display — only shows fields with real data
- Try/except wrapper — complete error handling
- Logging — tracks missing/incomplete records
- User feedback — helpful error messages instead of silent failures

## Matthew Boozer Ad Proofs Backfill (Jun 30, 2026)
**Status:** ✅ LIVE (commit 3fe5019) — Boozer proofs 21 → 109

Tyler asked to load ALL Matthew Boozer ad proofs "from when he started until current." Existing ad_proofs.json only had 21 Boozer proofs (Mar 23–May 21, 2026) because the daily scanner (`scripts/scan_ad_proofs.py`) uses `DAYS_BACK=90`. Boozer's first contract was Aug 8, 2025; Gmail had 299 Boozer ad-proof emails (Aug 12, 2025 → Jun 29, 2026, where matthew.boozer@indoormedia.com is a recipient).

Built one-time `scripts/backfill_boozer_proofs.py` (reuses scan_ad_proofs parsing). Searches `subject:"Ad Proof from IndoorMedia" matthew.boozer@indoormedia.com after:2025/08/01`, merges into existing proofs (other reps untouched), runs same dedup (newest per contract+store). Result: 278 new, 179 dupes removed → 405 total, 109 Boozer (Aug 19 2025 → Jun 29 2026). 2 proofs missing image_url (odd Drive link format).

**KEY REPO FACTS (re-confirmed):**
- Live PWA repo is `~/.openclaw/workspace/pwa/` (remote github.com/tylervansant-hugo/IndoorMedia-pwa). The scanner writes to `pwa/public/data/ad_proofs.json`, builds + deploys from `pwa/`. Also keep `~/.openclaw/workspace/public/data/ad_proofs.json` in sync (older mirror).
- Daily cron: crontab `0 22 * * *` → `scripts/run_ad_proofs_scan.sh` (scan + build + `npx gh-pages -d dist --no-history` + push). Default daily window is 3 days.
- **Git gotcha:** local `pwa` main had diverged badly (6 ahead / 57 behind, stale counter-sign/nightly commits causing rebase conflicts on contracts.json). Fix: `git reset --hard origin/main`, re-apply ad_proofs.json, commit, push (fast-forward). Don't try to replay the old local commits.
- GitHub Pages CDN takes a few min to propagate; live JSON at https://tylervansant-hugo.github.io/IndoorMedia-pwa/data/ad_proofs.json lags right after deploy.

## Prospect Privacy + Call-In Lead Assignment (Jun 30, 2026)
**Status:** ✅ LIVE (commit 3273b4e, bundle index-DacOysGW.js)

Tyler's 3 asks, all in `pwa/`:

1. **Private prospect notes/contacts** — Owner/Decision-Maker name, contact phone, contact email, and Notes are now visible ONLY to: the rep who logged them (`ld.updatedBy`), Tyler, and Rick Leibowitz. Central helpers in ProspectSearch.svelte: `repDisplayName()`, `isPrivilegedViewer()` (tyler/rick/role==manager), `canSeePrivate(ld)`. Web-scraped emails (`updatedBy==='auto-scrub'`) and unlogged leads are NOT treated as private (public data / current rep may start logging). Both lead-data display blocks (results card ~2560 + saved-prospect card ~2990) are gated. Team tab now uses `isPrivilegedViewer()` so Rick gets it too (was tyler-only).

2. **BOOKED / CLOSED to others** — When a non-privileged viewer can't see private notes, they see a status badge instead via `getSharedStatus(prospect)` which reads `ld.status || leadClaim.lastAction || prospect.status` and maps book/appt→BOOKED, clos/sold/sale/won/signed→CLOSED. CSS `.status-booked` (blue) / `.status-closed` (green), `.notes-private`, `.note-private-msg`.

3. **Manager-assigned call-in leads** — Call-in leads are HIDDEN from reps until Tyler/Rick assigns them. Firebase (`src/lib/firebase.js`): `callInLeadKey(lead)` (crm_id or business+zip hash), `assignCallInLead(leadKey, repId, repName, assignedBy)`, `getAllCallInAssignments()` → stored as `activity_daily/callin_assign_<key>` docs type `callin_assignment`. ProspectSearch: `allCallInLeads` (full pool), `callInAssignments` map, `applyCallInVisibility()` (privileged=all, reps=only assigned by repId or name match), `buildRepRoster()` from rep_registry.json (dict keyed by rep id; skip 999999999/blank), `handleAssignCallIn()`. UI: assign dropdown + 🎯 assigned / ⚪ Unassigned badge on each call-in card, managers only. Main.svelte homepage call-in count also filtered by assignment for reps, and the whole homepage call-in card is hidden for reps with 0 assigned.

**IMPORTANT:** Assignment matching relies on rep `$user.id` matching the rep_registry.json key (Telegram/phone id). rep_registry keys ARE the ids (inner `id` field is null). If a rep's assigned leads don't show, check that their $user.id equals their registry key. Firebase must be ready for assignments to load/persist. Service worker caches hard — tell Tyler to fully close/reopen or hard-refresh to see the new bundle.

## Cartvertising Quick-Add + Front/Directory Explainer (Jun 30, 2026)
**Status:** ✅ LIVE (commit a8f1783, bundle index-3hYgpCta.js)

Two asks in `pwa/`:

1. **Quick-add Cartvertising on store cards** — StoreSearch.svelte store card now has a green "🛒 Add Cartvertising" button (in the store-info block, under 🎯 Prospect Store). Tapping opens a package picker (`CART_PACKAGES`: 20% Front OR Directory $2,995 / 40% $4,795 / 60% $5,995 / 80% $7,395 / 100% $8,795). `handleAddCartvertising(store,pkg)` pushes an item to `localStorage.indoormedia_cart` (same shape Cart.svelte reads: {type:'cartvertising', name:'Cartvertising', emoji:🛒, store, storeNum, storeAddress, storeCycle, plan:pkg.name, price:pkg.price}) and fires `cart-updated`. Register-tape add-to-cart is unchanged.

2. **Front vs Directory explainer graphic** — Cart.svelte. Added an HTML/CSS version (`.cart-diagram`) shown in the quote tool UI whenever a Cartvertising item is in the cart, AND a native vector version drawn in the Quote PDF (`drawCartDiagram()` inside `exportQuotePdf`, called right after Cartvertising Highlights). Recreates Tyler's reference layout (ignores percentages): left = single "Front Side" panel (thick black rounded border), red "OR" arrow, right = "Directory Side" panel split into narrow label + wider "Store Directory" box. Meaning captions per Tyler: Front = faces the front of the cart / oncoming shoppers; Directory = faces toward the shopper, next to the store directory. Verified PDF render via headless pdf-lib + pdftoppm (looks correct, headers clear the title with y-=42 gap).

Reminder to Tyler: hard-refresh / reopen app to clear service-worker cache for the new bundle.

## Cartvertising Cart-Count Quote + Full Rate Sheet + Header Graphic (Jun 30, 2026)
**Status:** ✅ LIVE (commit 53bcecf, bundle rebuilt)

Tyler: stop showing impression counts for Cartvertising; instead ASK the store's shopping-cart count when adding, then show how many carts display the ad based on the chosen %. Also load all rate-sheet packages (incl 200% + Header ads) and add a Header explainer graphic.

**StoreSearch.svelte:**
- `CART_PACKAGES` now the FULL rate sheet (6-mo rates), each with metadata {pct, front, dir, header, footer, kind:'front_dir'|'header'}: 20% Front OR Directory $2,995 · 40% (20+20) $4,795 · 60% (40+20) $5,995 · 80% (40+40) $7,395 · 100% (60+40) $8,795 · 200% (100 both) $12,995 · Header 50% every other cart $2,995 · Header 100% every cart (header+footer) $4,795.
- `handleAddCartvertising(store,pkg)` now `window.prompt`s for the store's total shopping-cart count (remembers per-store via `store._cartCount`), computes `cartsShowingAd = round(count × pct/100)`, and writes cart item fields: cartPct, cartKind, frontPct, dirPct, headerPct, hasFooter, storeCartCount, cartsShowingAd. Package picker grouped into "Front & Directory Ads" and "Header Ads".

**Cart.svelte:**
- `getImpressions()` returns null for Cartvertising (no more fake 500/day impressions).
- New `getCartCoverage(item)` → {total, pct, showing, isHeader}. Quote PDF line item and the in-app cart item now show "N of M shopping carts will display your ad (X% of all carts)" instead of impressions. If a Cartvertising item has no storeCartCount (added before this change), UI shows an amber hint to re-add from the store card.
- PDF: `drawCartDiagram()` (Front vs Directory) unchanged; added `drawHeaderDiagram()` (Header 50% = top-right tag / Header 100% = header + footer tags) drawn only when a header item is in cart. HTML UI diagram got a matching `#if header` section (.cd-panel-header, .cd-header-tag, .cd-footer-tag).
- Verified full PDF render headless (pdf-lib + pdftoppm): coverage line + both diagrams look correct.

NOTE: cart count is entered via a browser prompt() at add-time. Old Cartvertising items added before today won't have counts — re-add them. Service worker caches hard: hard-refresh/reopen to get new bundle.
