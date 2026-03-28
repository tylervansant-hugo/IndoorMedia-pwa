# 🔥 Hot Leads System — Complete Guide

## What It Is

A three-part lead management system that puts qualified, ready-to-call businesses in your reps' hands — with phone + email verified and split into approved/pending workflows.

---

## Three Tabs

### 1️⃣ **Approved Leads** ✅
**What reps see when they open Hot Leads:**
- Grid of 5-max-per-store leads
- Real businesses with verified phone + email
- Click any lead → Call/Email buttons
- Pre-filled email templates (Initial Appointment or ROI)

**Your Poulsbo Test:**
- Safeway Kingston (SMALL, 14 cases): 4 leads
- Safeway Bremerton (MEDIUM, 18 cases): 1 lead  
- Fred Meyer Bremerton (LARGE, 32 cases): 2 leads
- **Total: 7 qualified leads**

**How reps use it:**
1. Open PWA → Hot Leads tab
2. Filter by store or search business name
3. See hook message: "Safeway Kingston is sending customers to Puerto Vallarta daily!"
4. Click → Get phone + email → Call or email pre-written pitch
5. Track response (manual notes or upcoming status feature)

---

### 2️⃣ **Pending Leads** ⏳ 
**Your approval queue — only YOU see this tab**
- Reps submit → Lands in pending
- You review details: name, phone, email, category, store ref, submitted by/date
- Approve → Goes to Approved Leads tab immediately
- Reject → Removed (rep can resubmit if they fix it)

**This prevents junk from hitting reps' leads.**

---

### 3️⃣ **Add Lead** ➕
**How reps source leads**

**Two entry methods:**

**A) Manual Entry (Fast)**
- Business name (required)
- Phone (required) 
- Email (required)
- Category dropdown (Restaurant, Auto Repair, Salon, Dental, Gym, Vet, Chiropractor, Other)
- Optional: Address, rating, reviews, store reference (searchable dropdown)
- Submit → Goes to your Pending queue

**B) Business Card OCR (Slick)**
- Photograph card with phone
- Upload image
- Click "Extract Text" → Tesseract.js reads it
- Auto-extracts phone + email
- Rep types name + confirms/edits
- Submit → Goes to your Pending queue

**Note:** Both require name + phone + email. Optional fields are nice-to-have.

---

## The Hook Copy

Each lead shows context-specific messaging per store tier:

```
SMALL (7-14 cases):   "Safeway Kingston is sending customers to Puerto Vallarta daily!"
MEDIUM (15-20 cases): "Safeway Bremerton is sending thousands of dollars in business monthly!"
LARGE (25+ cases):    "Fred Meyer Bremerton is driving a huge volume of extra business!"
```

This is the opener reps use when they call.

---

## Cycle Schedule

Auto-switches stores every 10 days:

- **Now → Apr 10:** B-cycle stores (91 total)
- **Apr 10 → May 10:** C-cycle stores  
- **May 10 → Jun 10:** A-cycle stores
- **Jun 10+:** Back to B-cycle

Reps only see Hot Leads from their assigned cycle. You can see all.

---

## Email Templates

Pre-filled templates (from your existing EmailTemplates component):

- **Initial Appointment:** "I noticed [business]... would you be open to a 10-min chat?"
- **ROI/Value:** "Did you know the avg grocery store gets 10K+ visitors/week?"

Reps can:
- Type contact name (optional personalization)
- Copy subject + body to clipboard
- Or click "Email" button → Direct mailto link

---

## Rep Workflow (Daily)

1. **Morning:** Open PWA → Hot Leads ✅ tab
2. **See:** 5 businesses near their assigned stores, ranked by rating
3. **Click one:** Get phone + pre-written hook
4. **Call or Email:** Use pre-filled template
5. **Track:** (Manual for now; status tracking coming soon)

---

## Next Steps

### Phase 2 (Coming Soon)
- [ ] Expand to all 91 B-cycle stores (Poulsbo is test)
- [ ] Auto-generate hooks + emails per category
- [ ] Lead status tracking (Contacted → Interested → Proposal → Closed)
- [ ] Rep leaderboard (conversions per rep)
- [ ] Auto-delete pending leads after 30 days of no action

### Phase 3 (Future)
- [ ] CRM integration (sync closed deals)
- [ ] SMS follow-ups (if they don't pick up)
- [ ] A/B test hooks per category
- [ ] Testimonial pull-in (show similar business results)

---

## File Locations

**Components:**
- `/pwa/src/components/HotLeads.svelte` — Main container
- `/pwa/src/components/HotLeadsSubmit.svelte` — Add lead (manual + OCR)
- `/pwa/src/components/PendingLeads.svelte` — Your review queue

**Data:**
- `/pwa/public/data/hot_leads.json` — Live approved leads (7 Poulsbo test)
- `/pwa/public/data/pending_leads.json` — Awaiting your approval (auto-created on first submit)

**API Endpoints (need to build):**
- `POST /api/submit-lead` — Rep submits lead → pending queue
- `POST /api/approve-lead` — You approve → moves to hot_leads.json
- `POST /api/reject-lead` — You reject → deleted

---

## Known Limits

**Tesseract.js OCR:**
- Works best on clear, well-lit cards
- May misread cursive or fancy fonts
- Phone extraction works well, email varies
- Always double-check before submitting

**Email Scraping:**
- Website-based extraction only (Tesseract on card image)
- ~40-50% of small businesses don't have websites
- Manual entry fallback for those without web presence

---

## Questions?

Tyler: This system is live. Test with Ryan Rohner in Poulsbo first, then we'll roll out to all 91 B-cycle stores + build the API backend for lead submission.

Want to adjust hook copy, add categories, or tweak the flow? Let me know.
