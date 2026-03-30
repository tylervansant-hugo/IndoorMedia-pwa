# PWA Enhancement Roadmap
**Priority: CRITICAL — Complete Prospect Feature Parity**

## Missing Prospect Features (From Telegram Bot)

### 1. Prospect Card Actions (MISSING)
When a prospect card is expanded, user should see:
- ✅ 📍 **Maps** — Google Maps link (external)
- ✅ 🗺️ **Mappoint** — IndoorMedia MapPoint (external)
- ❌ 💾 **Save** — Save prospect to database
- ❌ 🎬 **Video** — Show category-specific promo videos
- ❌ 📝 **Notes** — Add/edit notes about prospect
- ❌ 📅 **Calendar** — Schedule appointment via Google Calendar
- ❌ 📧 **Draft Email** — Generate personalized email template
- ❌ 📞 **Call Button** — Direct tel: link (already present, needs enhancement)
- ❌ 🌐 **Website Button** — Opens business website (already present, needs enhancement)

### 2. Business Data (MISSING/INCOMPLETE)
Current prospect cards show basic data. Need:
- ❌ **Opening Hours** — "Open now" / "Closed" status
- ❌ **Place ID** — Google Place ID for detailed lookups
- ❌ **Email** — Business email if available
- ❌ **Contact Name** — Business owner/manager name
- ❌ **Category Tags** — Detailed category (not just search keyword)
- ❌ **Advertising Signals** — Greet Magazine, Facebook Ads, etc.
- ✅ **Rating** — Already shown (but needs real data)
- ✅ **Review Count** — Already shown (but needs real data)
- ✅ **Distance** — Calculate from user location

### 3. Search & Discovery (NEEDS IMPROVEMENT)
- ✅ Categories + Subcategories — Present (66 total)
- ❌ **Real Google Places API** — Currently using Nominatim (free but limited)
- ❌ **Live "Open Now" Filter** — Show only businesses open right now
- ❌ **Advertising Signals Integration** — Show businesses already advertising
- ❌ **Exclusion Rules** — Filter out chains (McDonald's, Taco Bell, etc.)
- ❌ **Likelihood Scoring** — Real 0-100 score based on multiple factors

### 4. Saved Prospects (MISSING ENTIRELY)
- ❌ **Save to Local DB** — localStorage or IndexedDB
- ❌ **View Saved Prospects** — Separate tab/view
- ❌ **Search Saved Prospects** — Filter by status, category, notes
- ❌ **Status Updates** — New → Contacted → Proposal → Closed
- ❌ **Notes/History** — Track all interactions with prospect
- ❌ **Calendar Integration** — Link appointments to prospects

### 5. Email & Communication (MISSING)
- ❌ **Draft Email Button** — Generate email from template
- ❌ **Personalized Templates** — Use business name, category, testimonials
- ❌ **Email Send** — Open mailto: with pre-filled content
- ❌ **SMS Draft** — Generate text message template
- ❌ **Follow-up Reminders** — Schedule reminders for prospects

### 6. Video Integration (MISSING)
- ❌ **Category Videos** — Show relevant promo videos per category
- ❌ **Video Library** — Database of videos by category
- ❌ **Video Playback** — Inline or YouTube modal

---

## Implementation Plan

### Phase 1: Core Prospect Actions (Priority 1)
**Target: Tonight/Tomorrow**
1. Add "Show Actions" expandable button to prospect cards
2. Implement:
   - 💾 Save Prospect (localStorage)
   - 📝 Notes (modal/inline editor)
   - 📅 Calendar (Google Calendar link)
   - 📧 Draft Email (pre-filled mailto:)
   - 📍 Maps (Google Maps external link)
   - 🗺️ Mappoint (IndoorMedia link)

### Phase 2: Enhanced Business Data (Priority 2)
**Target: Weekend**
1. Integrate **Google Places API** (Tyler has key)
2. Fetch real business data:
   - Opening hours + "Open now" status
   - Website, phone, email
   - Place ID for lookups
   - Detailed ratings + reviews
3. Calculate **likelihood score** (0-100) based on:
   - Distance from store
   - Rating (higher = better)
   - Review count (more = active)
   - Open status (open = +10)
   - Advertising signals (+20 if found)

### Phase 3: Saved Prospects Database (Priority 2)
**Target: Weekend**
1. Create localStorage schema for saved prospects
2. Build "Saved Prospects" view
3. Add status workflow: New → Contacted → Proposal → Closed
4. Notes/history tracking
5. Search & filter saved prospects

### Phase 4: Video & Email Enhancements (Priority 3)
**Target: Next Week**
1. Build category video library
2. Email template personalization engine
3. SMS templates
4. Follow-up reminder system

---

## Google Places API Integration Plan

### Required API Calls
1. **Text Search** — Find businesses by keyword near location
   - Endpoint: `https://maps.googleapis.com/maps/api/place/textsearch/json`
   - Params: query, location, radius, type, opennow
2. **Place Details** — Get full business info
   - Endpoint: `https://maps.googleapis.com/maps/api/place/details/json`
   - Params: place_id, fields (name,rating,opening_hours,phone,website,email)

### API Key Location
Tyler provided key on Mar 11:
- File: `/Users/tylervansant/.openclaw/workspace/.env`
- Variable: `GOOGLE_PLACES_API_KEY`

### Implementation Strategy
- **Backend Function** (Vercel Serverless)
  - Create `/api/search-prospects.js` endpoint
  - Proxy Google Places API (hide key from client)
  - Add caching layer (24h TTL)
- **Fallback Strategy**
  - Primary: Google Places API
  - Fallback: Nominatim (free, no auth)
  - Last Resort: Sample prospects

---

## Next Actions (Tyler Approval Needed)

1. ✅ **Deploy Google Places API integration?**
   - Requires Vercel serverless function
   - Cost: ~$5/month for typical usage
   - Benefit: Real business data, opening hours, accurate ratings

2. ✅ **Build Saved Prospects database?**
   - localStorage (free, offline-capable)
   - IndexedDB for larger datasets (future)

3. ✅ **Video library integration?**
   - Need category → video mapping
   - Host videos on YouTube or Vimeo?

4. ✅ **Email template personalization?**
   - Use existing 5 templates from Email Templates tab
   - Auto-fill business name, category, nearby store

---

## Estimated Timeline

| Phase | Feature | Effort | Target |
|-------|---------|--------|--------|
| 1 | Prospect actions (Save, Notes, Calendar, Email, Maps) | 4-6 hours | Tonight |
| 2 | Google Places API + real data | 6-8 hours | Tomorrow |
| 3 | Saved prospects database | 4-6 hours | Sunday |
| 4 | Video library + email enhancements | 6-8 hours | Next week |

**Total: ~24-30 hours of development**

---

## Status
- [x] Audit complete
- [ ] Tyler approval
- [ ] Implementation start

**Created:** March 21, 2026 (21:18 PDT)
**Owner:** Shelldon
**Assignee:** TBD (spawn subagent or self-implement)
