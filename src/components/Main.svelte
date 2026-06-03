<script>
  import { onMount } from 'svelte';
  import { theme, user } from '../lib/stores.js';
  import { get } from 'svelte/store';

  // Parse contract dates safely — handles "2026-04-10 00:00", "2026-04-10", "4/10/2026"
  function parseContractDate(dateStr) {
    if (!dateStr) return new Date(0);
    // Strip time portion like " 00:00" or " 16:58"
    const dateOnly = dateStr.split(' ')[0];
    // Parse as local date (noon) to avoid UTC timezone shift
    const parts = dateOnly.includes('-') ? dateOnly.split('-') : null;
    if (parts && parts.length === 3) {
      return new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]), 12, 0, 0);
    }
    // M/D/YYYY format
    const slashParts = dateOnly.split('/');
    if (slashParts.length === 3) {
      return new Date(parseInt(slashParts[2]), parseInt(slashParts[0]) - 1, parseInt(slashParts[1]), 12, 0, 0);
    }
    return new Date(dateStr);
  }
  import { logActivity, getRepActivityReport, getDailySummaries } from '../lib/activity.js';
  import { initFirebase, isFirebaseReady, getAllRepActivity } from '../lib/firebase.js';
  import StoreSearch from './StoreSearch.svelte';
  import StoreMap from './StoreMap.svelte';
  import ProspectSearch from './ProspectSearch.svelte';
  import Tools from './Tools.svelte';
  import Cart from './Cart.svelte';
  import Products from './Products.svelte';
  import Present from './Present.svelte';
  import Clients from './Clients.svelte';
  import ManageReps from './ManageReps.svelte';
  import HotLeadsSubmit from './HotLeadsSubmit.svelte';
  import DrivingMode from './DrivingMode.svelte';

  let currentTab = 'dashboard';
  let previousTab = 'dashboard';
  let storesView = 'rates'; // 'rates', 'prospects', or 'map'
  let showDrivingMode = false;
  let _appEdgeSwipe = false;
  let _appEdgeStartX = 0;
  let _appEdgeDX = 0;
  
  // Track tab changes
  $: if (currentTab && typeof window !== 'undefined') {
    if (currentTab !== previousTab) previousTab = currentTab;
    logActivity('page_view', { tab: currentTab, rep: $user?.name || $user?.first_name || 'unknown' });
  }
  let currentTheme = 'light';
  let cartCount = 0;
  let contracts = [];
  let allStores = [];
  let savedProspects = [];
  let analyticsView = 'year';
  let analyticsZone = 'all';

  // Dashboard stats
  let prospectsThisWeek = 0;
  let prospectBreakdown = { saved: 0, searches: 0, calls: 0, savedNames: [], searchTerms: [], callNames: [] };
  let showProspectDetail = false;
  let revenueThisMonth = 0;
  let growthPercent = 0;
  let storesInTerritory = 0;
  let pendingRenewalsCount = 0;
  let leaderboardPosition = 0;
  let leaderboardTotal = 0;
  let repMonthlyRevenue = 0;
  let upcomingAppointments = [];
  let dailyGoal = { calls: 0, target: 0 };
  let streak = 0;
  let streakDays = []; // detailed streak history
  let nextCycleDate = '';
  let nextCycleName = '';
  let showRevenueDetail = false;
  let showStreakDetail = false;
  let analyticsExpandedRep = null;
  let showAppointmentsDetail = false;
  let appointmentsByRep = {}; // { rep_name: { count, appointments: [...] } }
  let thisMonthContracts = [];
  let thisWeekContracts = [];
  let thisWeekRevenue = 0;
  let weeklyBreakdown = []; // { weekLabel, contracts, revenue }
  let pendingRenewalsData = [];

  // Summer Sales Contest
  let summerSalesData = [];
  let showSummerSalesDetail = false;
  let companyLeads = [];

  // Motivational quotes
  const QUOTES = [
    { text: "Success is not final, failure is not fatal: it is the courage to continue that counts.", author: "Winston Churchill" },
    { text: "The only way to do great work is to love what you do.", author: "Steve Jobs" },
    { text: "Don't watch the clock; do what it does. Keep going.", author: "Sam Levenson" },
    { text: "Every sale has five basic obstacles: no need, no money, no hurry, no desire, no trust.", author: "Zig Ziglar" },
    { text: "Your attitude, not your aptitude, will determine your altitude.", author: "Zig Ziglar" },
    { text: "The difference between a successful person and others is not a lack of strength, but a lack of will.", author: "Vince Lombardi" },
    { text: "I never lose. I either win or I learn.", author: "Nelson Mandela" },
    { text: "The harder you work, the luckier you get.", author: "Gary Player" },
    { text: "People don't buy for logical reasons. They buy for emotional reasons.", author: "Zig Ziglar" },
    { text: "Hustle beats talent when talent doesn't hustle.", author: "Ross Simmonds" },
    { text: "Stop selling. Start helping.", author: "Zig Ziglar" },
    { text: "The secret of getting ahead is getting started.", author: "Mark Twain" },
    { text: "Be so good they can't ignore you.", author: "Steve Martin" },
    { text: "Fall seven times, stand up eight.", author: "Japanese Proverb" },
    { text: "The best time to plant a tree was 20 years ago. The second best time is now.", author: "Chinese Proverb" },
    { text: "Sales are contingent upon the attitude of the salesman, not the attitude of the prospect.", author: "W. Clement Stone" },
    { text: "The top salespeople in the world are not selling. They're serving.", author: "Lori Greiner" },
    { text: "You miss 100% of the shots you don't take.", author: "Wayne Gretzky" },
    { text: "Opportunities don't happen. You create them.", author: "Chris Grosser" },
    { text: "It's not about having the right opportunities. It's about handling the opportunities right.", author: "Mark Hunter" },
    { text: "What you do today can improve all your tomorrows.", author: "Ralph Marston" },
    { text: "Discipline is the bridge between goals and accomplishment.", author: "Jim Rohn" },
    { text: "A goal without a plan is just a wish.", author: "Antoine de Saint-Exupéry" },
    { text: "Make each day your masterpiece.", author: "John Wooden" },
    { text: "Champions keep playing until they get it right.", author: "Billie Jean King" },
    { text: "Action is the foundational key to all success.", author: "Pablo Picasso" },
    { text: "Don't be afraid to give up the good to go for the great.", author: "John D. Rockefeller" },
    { text: "Success usually comes to those who are too busy to be looking for it.", author: "Henry David Thoreau" },
    { text: "Small daily improvements are the key to staggering long-term results.", author: "Unknown" },
    { text: "The only limit to our realization of tomorrow will be our doubts of today.", author: "Franklin D. Roosevelt" },
  ];

  let quoteCopied = false;
  let copyTimer;
  let pressStart = 0;

  function copyQuoteText(text) {
    // Try clipboard API first, fallback to execCommand
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(() => {
        quoteCopied = true;
        setTimeout(() => { quoteCopied = false; }, 1500);
      }).catch(() => fallbackCopy(text));
    } else {
      fallbackCopy(text);
    }
  }

  function fallbackCopy(text) {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.left = '-9999px';
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
    quoteCopied = true;
    setTimeout(() => { quoteCopied = false; }, 1500);
  }

  function getTodaysQuote() {
    const now = new Date();
    const dayOfYear = Math.floor((now - new Date(now.getFullYear(), 0, 0)) / 86400000);
    return QUOTES[dayOfYear % QUOTES.length];
  }

  let nextInstallCycle = '';
  let nextInstallDate = '';
  let nextInstallDays = 0;
  let nextSellingCycle = '';
  let nextSellingDate = '';
  let nextSellingDays = 0;
  let currentSellingCycle = '';
  let currentSellingDates = '';
  let currentInstallCycle = '';
  let secondInstallCycle = '';
  let secondInstallDate = '';
  let secondInstallDays = 0;

  // Zone install day lookup — from RTUI Zone Chart
  const ZONE_INSTALL_DAYS = {
    '01':1,'02':8,'03':26,'04':28,'05':25,'06':1,'07':7,'08':5,'09':14,'10':30,
    '11':25,'12':16,'13':20,'14':10,'15':18,'16':7,'17':20,'18':20,'19':8,'20':10,
    '21':16,'22':1,'23':12,'24':14,'25':23,'26':20,'27':25,'28':6,'29':6
  };

  function getZoneInstallDay() {
    // Check user's zone field first (e.g., "24X" → zone "24")
    const userZone = $user?.zone || '';
    if (userZone) {
      const zm = userZone.match(/(\d{2})/);
      if (zm && ZONE_INSTALL_DAYS[zm[1]]) return ZONE_INSTALL_DAYS[zm[1]];
    }
    // Then check assigned stores
    const userStores = $user?.assigned_stores || [];
    if (userStores.length > 0) {
      const m = (userStores[0] || '').match(/(\d{2})[A-Z]?-/);
      if (m && ZONE_INSTALL_DAYS[m[1]]) return ZONE_INSTALL_DAYS[m[1]];
    }
    return 7; // default zone 07
  }

  function getNextCycle() {
    // Cycle schedule uses the zone-specific install day
    // A=Jan/Apr/Jul/Oct, B=Feb/May/Aug/Nov, C=Mar/Jun/Sep/Dec
    // Selling cycle switches 4 days after install
    const now = new Date();
    const installDay = getZoneInstallDay();
    const installCycles = [
      { name: 'A', months: [0, 3, 6, 9] },
      { name: 'B', months: [1, 4, 7, 10] },
      { name: 'C', months: [2, 5, 8, 11] },
    ];
    const sellingAfter = { 'A': 'C', 'B': 'A', 'C': 'B' };

    // Find next install date using zone-specific day
    let nearestInstall = null;
    for (const cycle of installCycles) {
      for (const m of cycle.months) {
        let d = new Date(now.getFullYear(), m, installDay);
        if (d <= now) d = new Date(now.getFullYear() + 1, m, installDay);
        if (!nearestInstall || d < nearestInstall.date) {
          nearestInstall = { date: d, name: cycle.name };
        }
      }
    }

    if (nearestInstall) {
      const diff = Math.ceil((nearestInstall.date - now) / 86400000);
      nextInstallCycle = nearestInstall.name;
      nextInstallDate = nearestInstall.date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      nextInstallDays = diff;

      // Find second install (the one after next)
      let secondInstall = null;
      for (const cycle of installCycles) {
        for (const m of cycle.months) {
          let d = new Date(now.getFullYear(), m, installDay);
          if (d <= nearestInstall.date) d = new Date(d.getFullYear() + 1, m, installDay);
          if (!secondInstall || d < secondInstall.date) {
            secondInstall = { date: d, name: cycle.name };
          }
        }
      }
      if (secondInstall) {
        secondInstallCycle = secondInstall.name;
        secondInstallDate = secondInstall.date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        secondInstallDays = Math.ceil((secondInstall.date - now) / 86400000);
      }

      // Selling cycle starts 4 days after install
      const sellDate = new Date(nearestInstall.date);
      sellDate.setDate(sellDate.getDate() + 4);
      const sellDiff = Math.ceil((sellDate - now) / 86400000);
      nextSellingCycle = sellingAfter[nearestInstall.name];
      nextSellingDate = sellDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      nextSellingDays = sellDiff;

      // Current cycle: what we're selling NOW and what installs from it
      // The selling cycle that's active is the one BEFORE the next selling cycle
      const cycleOrder = ['A', 'B', 'C'];
      const sellingInstall = { 'A': 'B', 'B': 'C', 'C': 'A' }; // selling A → installs as B
      currentSellingCycle = sellingAfter[nearestInstall.name]; // same as nextSellingCycle label
      // Actually: current selling = the cycle we're in right now
      // If next install is B (May 7), we're currently selling A (which installs as A on May 7? No...)
      // Cycle logic: selling C now → A install on Apr 7 already happened → next is B install May 7
      // So current selling cycle is the one whose selling window we're in
      // Selling window = from previous install+4 to next install+4
      // If next install is B on May 7, and next selling is A on May 11
      // Then CURRENT selling is C (Apr 11 to May 10), with A install (Apr 7)
      const prevInstallCycleName = sellingAfter[sellingAfter[nearestInstall.name]]; // two before next
      currentSellingCycle = prevInstallCycleName === 'A' ? 'C' : prevInstallCycleName === 'B' ? 'A' : 'B';
      // Simpler: current selling cycle is what comes before next selling
      // Next selling is A → current selling is C
      // Next selling is B → current selling is A  
      // Next selling is C → current selling is B
      const currentSellMap = { 'A': 'C', 'B': 'A', 'C': 'B' };
      currentSellingCycle = currentSellMap[nextSellingCycle];
      currentInstallCycle = sellingInstall[currentSellingCycle] || currentSellingCycle;
      
      // Current selling dates: from last selling start to next install+3
      const prevSellStart = new Date(nearestInstall.date);
      prevSellStart.setMonth(prevSellStart.getMonth() - 1);
      prevSellStart.setDate(installDay + 4);
      const currentSellEnd = new Date(nearestInstall.date);
      currentSellEnd.setDate(currentSellEnd.getDate() + 3);
      currentSellingDates = `${prevSellStart.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} – ${currentSellEnd.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`;
    }
  }

  // Sync key uses user ID so goals persist per-rep across devices via shared storage
  function getGoalKey() {
    const uid = $user?.id || 'default';
    return `impro_daily_goal_${uid}`;
  }

  let repSyncData = {};

  async function loadRepSync() {
    try {
      const res = await fetch(import.meta.env.BASE_URL + 'data/rep_sync.json?t=' + Date.now());
      repSyncData = await res.json();
    } catch { repSyncData = {}; }
  }

  function loadDailyGoal() {
    try {
      const today = new Date().toISOString().slice(0, 10);
      // Try user-specific key first, fall back to old key for migration
      let saved = JSON.parse(localStorage.getItem(getGoalKey()) || 'null');
      if (!saved) {
        saved = JSON.parse(localStorage.getItem('impro_daily_goal') || '{}');
        // Migrate to new key
        if (saved.date) localStorage.setItem(getGoalKey(), JSON.stringify(saved));
      }
      if (saved.date === today) {
        dailyGoal = saved;
      } else {
        dailyGoal = { date: today, target: saved.target || 20, calls: 0 };
      }
    } catch { dailyGoal = { date: new Date().toISOString().slice(0, 10), target: 20, calls: 0 }; }
  }

  function saveDailyGoal() {
    dailyGoal.date = new Date().toISOString().slice(0, 10);
    localStorage.setItem(getGoalKey(), JSON.stringify(dailyGoal));
    // Also save to old key for backward compat
    localStorage.setItem('impro_daily_goal', JSON.stringify(dailyGoal));
  }

  // Manager email for appointment invites
  const MANAGER_EMAIL = 'tyler.vansant@indoormedia.com';

  let syncStatus = '';
  
  // Google Apps Script URL for live calendar data
  // Set this after deploying the Apps Script (scripts/google_apps_script_calendar.js)
  const CALENDAR_API_URL = 'https://script.googleusercontent.com/a/macros/indoormedia.com/echo?user_content_key=AWDtjMU_lHT0xNAWQkyU5hat-v6ZCGwjFviNlJZf-5KUwna65c55MOdInmDLngcWY6OnpRvF2wh-w9gpkYQrEsTdeDIPtqgE_Vgf-EVAi1wK-UZrSt1dwwm_EL3SjUIWCq4Z1bMoGK20oFP6EU9n7LlUR4ahD_W4zgvPQejQpRsHGTKuiICLTCPNz-19KsQEploptlg4OLbVOBwk1xnsBxJ8sT-4Mgq_BkxVM7_HhUWXCjNCStMuueUe5yF8lfHfZIjyLGuGJhVWNMsk1Z970rGUMuh739WyXHpHditxf0Vd8moEH2wDY233FTBCngTVl8GPhaSgoaP-&lib=Mzz3mqyJSZ0ql-JCrrMKeASMMJ0XCjnoQ';

  async function refreshAppointments() {
    syncStatus = '🔄 Syncing...';
    try {
      let data;
      
      // Try live Google Apps Script first, fall back to static file
      if (CALENDAR_API_URL) {
        try {
          const sep = CALENDAR_API_URL.includes('?') ? '&' : '?';
          const liveRes = await fetch(CALENDAR_API_URL + sep + 'days=30&t=' + Date.now());
          data = await liveRes.json();
          if (data.error) throw new Error(data.error);
          syncStatus = '🔄 Live sync...';
        } catch {
          // Fall back to static
          const res = await fetch(import.meta.env.BASE_URL + 'data/appointments.json?t=' + Date.now());
          data = await res.json();
        }
      } else {
        const res = await fetch(import.meta.env.BASE_URL + 'data/appointments.json?t=' + Date.now());
        data = await res.json();
      }
      
      const now = new Date();
      const repName = ($user?.name || $user?.first_name || '').toLowerCase();
      const isManagerUser = repName.includes('tyler') || $user?.role === 'manager';
      
      const upcoming = (isManagerUser ? data : data.filter(a => {
        const creator = (a.creator || '').toLowerCase();
        const attendees = (a.attendees || []).map(att => (att.email || att || '').toLowerCase());
        return creator.includes(repName.split(' ')[0]) || attendees.some(e => e.includes(repName.split(' ')[0]));
      })).filter(a => new Date(a.start) >= now)
        .map(a => ({
          event_id: a.event_id,
          title: a.title,
          date: a.start,
          end: a.end,
          location: a.location,
          description: a.description || '',
          attendees: a.attendees || [],
          type: a.is_prospect_visit ? 'prospect' : 'calendar',
          store: a.store,
          phone: a.phone
        }));
      
      // Deduplicate by title + exact start time (not event_id — recurring events share IDs)
      const seen = new Set();
      const deduped = upcoming.filter(a => {
        const key = (a.title || '') + '|' + (a.date || '');
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      }).sort((a, b) => new Date(a.date) - new Date(b.date));
      
      upcomingAppointments = deduped;
      
      // Group appointments by rep
      appointmentsByRep = {};
      deduped.forEach(appt => {
        const repName = appt.rep || 'Unassigned';
        if (!appointmentsByRep[repName]) {
          appointmentsByRep[repName] = { count: 0, appointments: [] };
        }
        appointmentsByRep[repName].count += 1;
        appointmentsByRep[repName].appointments.push(appt);
      });
      
      syncStatus = `✅ ${upcomingAppointments.length} upcoming`;
      setTimeout(() => syncStatus = '', 3000);
    } catch (e) {
      syncStatus = '❌ Sync failed';
      setTimeout(() => syncStatus = '', 3000);
    }
  }

  function bookAppointment(prospect = null) {
    const repName = $user?.name || $user?.first_name || '';
    const repEmail = '';
    const title = prospect ? `IndoorMedia — ${prospect.business_name || prospect.name || 'Prospect Visit'}` : 'IndoorMedia — Prospect Visit';
    const location = prospect?.address || '';
    const details = prospect ? `Meeting with ${prospect.contact_name || prospect.business_name || 'prospect'}\\nStore: ${prospect.store || ''}\\nPhone: ${prospect.phone || ''}\\nRep: ${repName}` : `Sales appointment\\nRep: ${repName}`;
    
    // Default to tomorrow at 10am, 1 hour
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    tomorrow.setHours(10, 0, 0, 0);
    const end = new Date(tomorrow);
    end.setHours(11, 0, 0, 0);
    
    const fmt = d => d.toISOString().replace(/[-:]/g, '').split('.')[0] + 'Z';
    
    // Google Calendar URL with manager auto-invited
    const gcalUrl = `https://calendar.google.com/calendar/render?action=TEMPLATE&text=${encodeURIComponent(title)}&dates=${fmt(tomorrow)}/${fmt(end)}&details=${encodeURIComponent(details)}&location=${encodeURIComponent(location)}&add=${encodeURIComponent(MANAGER_EMAIL)}`;
    
    window.open(gcalUrl, '_blank');
  }

  async function getActivityData() {
    const local = getRepActivityReport();
    
    // Try to get cross-device data from Firebase
    if (isFirebaseReady()) {
      try {
        const allActivity = await getAllRepActivity(7);
        if (allActivity.length > 0) {
          // Group by rep
          const byRep = {};
          allActivity.forEach(a => {
            if (!byRep[a.repName]) byRep[a.repName] = { logins: 0, pageViews: 0, searches: 0, calls: 0, emails: 0, lastActive: '', days: new Set() };
            const r = byRep[a.repName];
            r.logins += a.logins || 0;
            r.pageViews += a.pageViews || 0;
            r.searches += a.searches || 0;
            r.calls += a.calls || 0;
            r.emails += a.emails || 0;
            r.days.add(a.date);
            if (a.lastActive > r.lastActive) r.lastActive = a.lastActive;
          });
          
          local.allReps = Object.entries(byRep).map(([name, data]) => ({
            name,
            ...data,
            activeDays: data.days.size,
            lastActive: data.lastActive ? new Date(data.lastActive).toLocaleString() : 'Never'
          })).sort((a, b) => b.pageViews - a.pageViews);
          
          local.firebaseConnected = true;
        }
      } catch (e) {
        console.warn('Firebase activity fetch error:', e);
      }
    }
    
    local.firebaseConnected = local.firebaseConnected || false;
    local.allReps = local.allReps || [];
    return local;
  }

  let swipingIndex = -1;
  let swipeStart = 0;

  function handleSwipeStart(e, idx) {
    swipeStart = e.touches?.[0]?.clientX || 0;
    swipingIndex = idx;
  }

  function handleSwipeEnd(e, idx) {
    const swipeEnd = e.changedTouches?.[0]?.clientX || 0;
    const diff = swipeStart - swipeEnd;
    if (diff > 50) {
      // Swiped left — delete
      upcomingAppointments = upcomingAppointments.filter((_, i) => i !== idx);
    }
    swipingIndex = -1;
  }

  function openInCalendar(event) {
    // Open Google Calendar event (event_id format: Gxx@google.com or similar)
    if (event.event_id && event.event_id.includes('@')) {
      window.open(`https://calendar.google.com/calendar/r/eventedit/${event.event_id}`, '_blank');
    } else {
      // Fallback: open Google Calendar to create event
      const start = new Date(event.date);
      const end = new Date(event.end || new Date(start.getTime() + 60 * 60 * 1000));
      const fmt = d => d.toISOString().replace(/[-:]/g, '').split('.')[0] + 'Z';
      window.open(`https://calendar.google.com/calendar/render?action=TEMPLATE&text=${encodeURIComponent(event.title)}&dates=${fmt(start)}/${fmt(end)}&location=${encodeURIComponent(event.location || '')}`, '_blank');
    }
  }

  function incrementCalls() {
    dailyGoal.calls = (dailyGoal.calls || 0) + 1;
    dailyGoal = dailyGoal;
    saveDailyGoal();
  }

  function setGoalTarget(val) {
    dailyGoal.target = parseInt(val) || 20;
    dailyGoal = dailyGoal;
    saveDailyGoal();
  }

  function resetDailyGoal() {
    dailyGoal.calls = 0;
    dailyGoal = dailyGoal;
    saveDailyGoal();
  }

  function calcStreak() {
    try {
      const searches = JSON.parse(localStorage.getItem('impro_searches') || '[]');
      const calls = JSON.parse(localStorage.getItem('impro_phone_clicks') || '[]');
      
      // Build daily activity detail
      const byDay = {};
      searches.forEach(x => {
        const d = new Date(x.date).toISOString().slice(0, 10);
        if (!byDay[d]) byDay[d] = { date: d, searches: 0, calls: 0 };
        byDay[d].searches++;
      });
      calls.forEach(x => {
        const d = new Date(x.date).toISOString().slice(0, 10);
        if (!byDay[d]) byDay[d] = { date: d, searches: 0, calls: 0 };
        byDay[d].calls++;
      });
      streakDays = Object.values(byDay).sort((a, b) => b.date.localeCompare(a.date)).slice(0, 14);
      
      const unique = new Set(Object.keys(byDay));
      let s = 0;
      const today = new Date().toISOString().slice(0, 10);
      let checkDate = today;
      for (let i = 0; i < 365; i++) {
        const d = new Date(checkDate + 'T12:00:00');
        const dayOfWeek = d.getDay(); // 0=Sun, 6=Sat
        const isWeekend = dayOfWeek === 0 || dayOfWeek === 6;
        
        if (unique.has(checkDate)) {
          s++;
        } else if (isWeekend) {
          // Skip weekends — don't break the streak and don't count them
        } else if (checkDate !== today) {
          // Missed a weekday (not today) — streak broken
          break;
        }
        d.setDate(d.getDate() - 1);
        checkDate = d.toISOString().slice(0, 10);
      }
      streak = s;
    } catch { streak = 0; }
  }

  function updateCartCount() {
    try { cartCount = JSON.parse(localStorage.getItem('indoormedia_cart') || '[]').length; } catch { cartCount = 0; }
  }

  function computeSummerSales() {
    const startDate = new Date(2026, 4, 27); // May 27
    const endDate = new Date(2026, 8, 1);    // Sep 1
    companyLeads = JSON.parse(localStorage.getItem('summer_sales_company_leads') || '[]');

    const summerContracts = contracts.filter(c => {
      const d = parseContractDate(c.date);
      return d >= startDate && d < endDate;
    });

    const repPoints = {};
    summerContracts.forEach(c => {
      const rep = c.sales_rep || 'Unknown';
      if (!repPoints[rep]) repPoints[rep] = { points: 0, deals: 0, details: [] };

      const isDigital = (c.product_type === 'digital') ||
        /FindLocal|ReviewBoost|LoyaltyBoost|DigitalBoost/i.test(c.product_description || '');
      const isRenewal = c.is_renewal === true;
      const isCompanyLead = companyLeads.includes(c.contract_number);
      const isPaidInFull = c.paid_in_full === true;

      let points = 1;
      let note = '';

      // Renewal tape = 0 points
      if (isRenewal && !isDigital) {
        points = 0;
        note = 'Renewal (tape)';
      } else if (isCompanyLead) {
        points = 0.5;
        note = 'Company lead';
      } else if (isRenewal && isDigital) {
        note = 'Renewal (digital)';
      }

      // Paid in Full bonus: +1 point (only if not excluded by renewal tape)
      if (isPaidInFull && !(isRenewal && !isDigital)) {
        points += 1;
        note = note ? note + ' + PIF' : 'Paid in Full';
      }

      repPoints[rep].points += points;
      repPoints[rep].deals += 1;
      repPoints[rep].details.push({
        business: c.business_name,
        product: c.product_description || c.product_type || '',
        amount: c.total_amount || 0,
        points,
        note,
        contract_number: c.contract_number,
        isCompanyLead,
        date: c.date,
      });
    });

    summerSalesData = Object.entries(repPoints)
      .map(([rep, data]) => ({ rep, ...data, expanded: false }))
      .sort((a, b) => b.points - a.points);
  }

  function toggleCompanyLead(contractNumber) {
    let leads = JSON.parse(localStorage.getItem('summer_sales_company_leads') || '[]');
    if (leads.includes(contractNumber)) {
      leads = leads.filter(n => n !== contractNumber);
    } else {
      leads.push(contractNumber);
    }
    localStorage.setItem('summer_sales_company_leads', JSON.stringify(leads));
    computeSummerSales();
  }

  function computeDashboardStats() {
    const repName = ($user?.name || $user?.first_name || '').toLowerCase();
    const isManager = repName.includes('tyler') || $user?.role === 'manager' || $user?.role === 'admin';
    const now = new Date();
    
    // Saved prospects this week (check both key formats)
    try {
      const saved1 = JSON.parse(localStorage.getItem('savedProspects') || '[]');
      const saved2 = JSON.parse(localStorage.getItem('saved_prospects') || '[]');
      const saved = saved1.length > saved2.length ? saved1 : saved2;
      const weekAgo = new Date(now);
      weekAgo.setDate(weekAgo.getDate() - 7);
      savedProspects = saved;
      
      // Count saved prospects this week
      const savedThisWeek = saved.filter(p => {
        const d = new Date(p.savedAt || p.saved_at || 0);
        return d >= weekAgo;
      }).length;
      
      // Count searches this week
      const searches = JSON.parse(localStorage.getItem('impro_searches') || '[]');
      const recentSearches = searches.filter(s => new Date(s.date) >= weekAgo);
      const searchesThisWeek = recentSearches.length;
      
      // Count phone clicks this week
      const phoneCalls = JSON.parse(localStorage.getItem('impro_phone_clicks') || '[]');
      const recentCalls = phoneCalls.filter(c => parseContractDate(c.date) >= weekAgo);
      const callsThisWeek = recentCalls.length;
      
      // Total activity = saved + searches + phone clicks
      prospectsThisWeek = savedThisWeek + searchesThisWeek + callsThisWeek;
      if (prospectsThisWeek === 0) prospectsThisWeek = saved.length;

      // Store breakdown for detail view
      prospectBreakdown = {
        saved: savedThisWeek,
        searches: searchesThisWeek,
        calls: callsThisWeek,
        savedNames: saved.filter(p => { try { return new Date(p.savedAt) >= weekAgo; } catch { return false; } }).map(p => ({ name: p.name, date: p.savedAt })).slice(0, 20),
        searchTerms: recentSearches.map(s => ({ category: s.category || s.subcategory || '', store: s.store || '', date: s.date })).slice(0, 20),
        callNames: recentCalls.map(c => ({ name: c.name || c.business || '', phone: c.phone || '', date: c.date })).slice(0, 20),
      };
    } catch { prospectsThisWeek = 0; }

    // Revenue this month from contracts
    const thisMonth = now.getMonth();
    const thisYear = now.getFullYear();
    const lastMonth = thisMonth === 0 ? 11 : thisMonth - 1;
    const lastMonthYear = thisMonth === 0 ? thisYear - 1 : thisYear;
    
    const myContracts = isManager ? contracts : contracts.filter(c => {
      const rep = (c.sales_rep || '').toLowerCase();
      return rep.includes(repName.split(' ')[0]);
    });
    
    thisMonthContracts = myContracts.filter(c => {
      const d = parseContractDate(c.date);
      return d.getMonth() === thisMonth && d.getFullYear() === thisYear;
    });
    const lastMonthContracts = myContracts.filter(c => {
      const d = parseContractDate(c.date);
      return d.getMonth() === lastMonth && d.getFullYear() === lastMonthYear;
    });
    
    revenueThisMonth = thisMonthContracts.reduce((sum, c) => sum + (c.total_amount || 0), 0);
    console.log('[Dashboard] isManager:', isManager, 'repName:', repName, 'contracts:', contracts.length, 'myContracts:', myContracts.length, 'thisMonth:', thisMonth, 'thisMonthContracts:', thisMonthContracts.length, 'revenue:', revenueThisMonth);
    
    // This week's contracts (Mon-Sun)
    const today = new Date();
    const dayOfWeek = today.getDay();
    const mondayOffset = dayOfWeek === 0 ? 6 : dayOfWeek - 1;
    const weekStart = new Date(today);
    weekStart.setDate(today.getDate() - mondayOffset);
    weekStart.setHours(0, 0, 0, 0);
    
    thisWeekContracts = myContracts.filter(c => {
      const d = parseContractDate(c.date);
      return d >= weekStart;
    });
    thisWeekRevenue = thisWeekContracts.reduce((sum, c) => sum + (c.total_amount || 0), 0);
    
    // Weekly breakdown for the current month
    const firstOfMonth = new Date(thisYear, thisMonth, 1);
    const weeks = [];
    let wStart = new Date(firstOfMonth);
    // Align to Monday
    const dow = wStart.getDay();
    if (dow !== 1) wStart.setDate(wStart.getDate() - (dow === 0 ? 6 : dow - 1));
    
    while (wStart.getMonth() <= thisMonth || (wStart.getMonth() === 0 && thisMonth === 11)) {
      const wEnd = new Date(wStart);
      wEnd.setDate(wEnd.getDate() + 6);
      wEnd.setHours(23, 59, 59, 999);
      
      const weekContracts = thisMonthContracts.filter(c => {
        const d = parseContractDate(c.date);
        return d >= wStart && d <= wEnd;
      });
      
      const startLabel = wStart.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      const endLabel = wEnd.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      const isCurrentWeek = today >= wStart && today <= wEnd;
      
      weeks.push({
        weekLabel: `${startLabel} – ${endLabel}`,
        contracts: weekContracts,
        revenue: weekContracts.reduce((s, c) => s + (c.total_amount || 0), 0),
        count: weekContracts.length,
        isCurrent: isCurrentWeek
      });
      
      wStart = new Date(wEnd);
      wStart.setDate(wStart.getDate() + 1);
      wStart.setHours(0, 0, 0, 0);
      if (wStart.getMonth() > thisMonth && wStart.getFullYear() >= thisYear) break;
      if (weeks.length > 6) break;
    }
    weeklyBreakdown = weeks;
    const lastMonthRevenue = lastMonthContracts.reduce((sum, c) => sum + (c.total_amount || 0), 0);
    growthPercent = lastMonthRevenue > 0 ? Math.round(((revenueThisMonth - lastMonthRevenue) / lastMonthRevenue) * 100) : 0;

    // Stores in territory (based on user's state)
    const userLocation = $user?.base_location || '';
    const userState = userLocation.split(',').pop()?.trim().toUpperCase() || '';
    if (isManager) {
      storesInTerritory = allStores.filter(s => s.State === 'OR' || s.State === 'WA').length;
    } else if (userState) {
      storesInTerritory = allStores.filter(s => s.State === userState).length;
    } else {
      storesInTerritory = allStores.length;
    }

    // Set monthly revenue (team total if manager, individual if rep)
    repMonthlyRevenue = revenueThisMonth;

    // Leaderboard — rank by this month's revenue
    const repTotals = {};
    contracts.filter(c => {
      const d = parseContractDate(c.date);
      return d.getMonth() === thisMonth && d.getFullYear() === thisYear;
    }).forEach(c => {
      const rep = c.sales_rep || 'Unknown';
      repTotals[rep] = (repTotals[rep] || 0) + (c.total_amount || 0);
    });
    const ranked = Object.entries(repTotals).sort((a, b) => b[1] - a[1]);
    leaderboardTotal = ranked.length;
    const myRank = ranked.findIndex(([rep]) => {
      return rep.toLowerCase().includes(repName.split(' ')[0]);
    });
    leaderboardPosition = myRank >= 0 ? myRank + 1 : 0;

    // Pending renewals count + add renewal value to revenue
    fetch(import.meta.env.BASE_URL + 'data/pending_renewals.json?t=' + Date.now())
      .then(r => r.json())
      .then(renewals => {
        if (isManager) {
          pendingRenewalsData = renewals;
          pendingRenewalsCount = renewals.length;
        } else {
          pendingRenewalsData = renewals.filter(r => (r.rep || '').toLowerCase().includes(repName.split(' ')[0]));
          pendingRenewalsCount = pendingRenewalsData.length;
        }

      })
      .catch(() => { pendingRenewalsCount = 0; pendingRenewalsData = []; });

    // Upcoming appointments — try live Google Calendar API first, fall back to static
    const calUrl = CALENDAR_API_URL
      ? CALENDAR_API_URL + (CALENDAR_API_URL.includes('?') ? '&' : '?') + 't=' + Date.now()
      : import.meta.env.BASE_URL + 'data/appointments.json?t=' + Date.now();
    
    fetch(calUrl)
      .then(r => r.json())
      .then(appts => {
        // If live API returned an error, fall back to static
        if (appts.error) throw new Error(appts.error);
        const repEmail = ($user?.email || '').toLowerCase();
        const rn = repName.toLowerCase();
        const isAdmin = rn.includes('tyler') || rn.includes('rick');
        
        // Filter: managers see all, reps see only events they created or are invited to
        const myAppts = isAdmin ? appts : appts.filter(a => {
          // Check if rep is creator
          if ((a.creator || '').toLowerCase().includes(rn.split(' ')[0])) return true;
          // Check if rep is in attendees
          return (a.attendees || []).some(att => {
            const attEmail = (att.email || '').toLowerCase();
            return attEmail.includes(rn.split(' ')[0]) || (repEmail && attEmail === repEmail);
          });
        });
        
        // Filter to future events, sort by date, deduplicate
        const upcoming = myAppts.filter(a => new Date(a.start) >= now)
          .sort((a, b) => new Date(a.start) - new Date(b.start))
          .map(a => ({
            event_id: a.event_id,
            title: a.title,
            date: a.start,
            end: a.end,
            location: a.location,
            description: a.description || '',
            attendees: a.attendees || [],
            type: a.is_prospect_visit ? 'prospect' : 'calendar',
            store: a.store,
            phone: a.phone,
          }));
        const initSeen = new Set();
        upcomingAppointments = upcoming.filter(a => {
          const k = (a.title || '') + '|' + (a.date || '');
          if (initSeen.has(k)) return false;
          initSeen.add(k);
          return true;
        });
      })
      .catch(() => {
        // Fall back to static file if live API fails
        fetch(import.meta.env.BASE_URL + 'data/appointments.json?t=' + Date.now())
          .then(r => r.json())
          .then(appts => {
            const upcoming = appts.filter(a => new Date(a.start) >= now)
              .sort((a, b) => new Date(a.start) - new Date(b.start))
              .map(a => ({ title: a.title, date: a.start, end: a.end, location: a.location, attendees: a.attendees || [], type: a.is_prospect_visit ? 'prospect' : 'calendar' }));
            upcomingAppointments = upcoming.slice(0, 12);
          })
          .catch(() => { upcomingAppointments = []; });
      });

    getNextCycle();
    loadDailyGoal();
    calcStreak();
    loadRepSync();
    initFirebase();
    computeSummerSales();
  }

  onMount(async () => {
    theme.subscribe(t => currentTheme = t);
    updateCartCount();
    const interval = setInterval(updateCartCount, 2000);

    try {
      const [contractsRes, storesRes] = await Promise.all([
        fetch(import.meta.env.BASE_URL + 'data/contracts.json?t=' + Date.now()),
        fetch(import.meta.env.BASE_URL + 'data/stores.json?t=' + Date.now())
      ]);
      const contractsData = await contractsRes.json();
      contracts = contractsData.contracts || [];
      console.log('[Dashboard] Loaded contracts:', contracts.length);
      allStores = await storesRes.json().catch(() => []);
      console.log('[Dashboard] Loaded stores:', allStores.length);
      try {
        computeDashboardStats();
      } catch (statsErr) {
        console.error('[Dashboard] computeDashboardStats ERROR:', statsErr);
      }
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    }

    // URL parameter actions (for Siri Shortcuts / deep links)
    const params = new URLSearchParams(window.location.search);
    if (params.get('mode') === 'driving') {
      showDrivingMode = true;
      // Clean URL
      window.history.replaceState({}, '', window.location.pathname);
    }
    if (params.get('action') === 'logcall') {
      incrementCalls();
      window.history.replaceState({}, '', window.location.pathname);
    }

    // Listen for map action events (Prospect/Rates from StoreMap popups)
    function handleMapAction(e) {
      const { action, store } = e.detail || {};
      if (action === 'prospect') {
        storesView = 'prospects';
        currentTab = 'stores';
        // Tell ProspectSearch to select this store and jump to categories
        if (store) {
          setTimeout(() => {
            document.dispatchEvent(new CustomEvent('select-store-from-map', { detail: store }));
          }, 300);
        }
      } else if (action === 'rates') {
        storesView = 'rates';
        currentTab = 'stores';
      }
    }
    document.addEventListener('map-action', handleMapAction);

    return () => {
      clearInterval(interval);
      document.removeEventListener('map-action', handleMapAction);
    };
  });

  // Reactive filtered contracts — triggers re-render when analyticsZone changes
  $: filteredContracts = analyticsZone === 'all' ? contracts : contracts.filter(c => (c.zone || '') === analyticsZone);
  $: yearlyStats = calcYearlyStats(filteredContracts);
  $: monthlyStats = calcMonthlyStats(filteredContracts);
  $: repStats = calcRepStats(filteredContracts);

  function getFilteredContracts() {
    return filteredContracts;
  }

  function getAvailableZones() {
    const zones = new Set();
    contracts.forEach(c => { if (c.zone) zones.add(c.zone); });
    return Array.from(zones).sort();
  }

  function calcYearlyStats(filtered) {
    const byYear = {};
    filtered.forEach(c => {
      const date = c.date || '';
      if (!date) return;
      try {
        const year = date.includes('/') ? new Date(date).getFullYear() : parseInt(date.substring(0, 4));
        if (!byYear[year]) byYear[year] = { year, total: 0, count: 0 };
        byYear[year].total += c.total_amount || 0;
        byYear[year].count += 1;
      } catch {}
    });
    const sorted = Object.values(byYear).sort((a, b) => b.year - a.year);
    sorted.forEach((stat, i) => {
      const prior = sorted[i + 1];
      stat.change = prior ? ((stat.total - prior.total) / prior.total) * 100 : null;
    });
    return sorted;
  }

  function calcMonthlyStats(filtered) {
    const byMonth = {};
    filtered.forEach(c => {
      const date = c.date || '';
      if (!date) return;
      try {
        const d = date.includes('/') ? new Date(date) : new Date(date.substring(0, 10));
        const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
        if (!byMonth[key]) byMonth[key] = { key, total: 0, count: 0 };
        byMonth[key].total += c.total_amount || 0;
        byMonth[key].count += 1;
      } catch {}
    });
    return Object.values(byMonth).sort((a, b) => b.key.localeCompare(a.key)).map(m => ({
      ...m,
      label: new Date(m.key + '-01').toLocaleDateString('en-US', { year: 'numeric', month: 'short' })
    }));
  }

  function calcRepStats(filtered) {
    const byRep = {};
    filtered.forEach(c => {
      const rep = c.sales_rep || 'Unknown';
      const date = c.date || '';
      let year = 0;
      try {
        year = date.includes('/') ? new Date(date).getFullYear() : parseInt(date.substring(0, 4));
      } catch {}
      if (!byRep[rep]) byRep[rep] = { rep, y2025: 0, y2026: 0, total: 0, count: 0 };
      const amt = c.total_amount || 0;
      byRep[rep].total += amt;
      byRep[rep].count += 1;
      if (year === 2025) byRep[rep].y2025 += amt;
      if (year === 2026) byRep[rep].y2026 += amt;
    });
    return Object.values(byRep).sort((a, b) => b.total - a.total);
  }

  function toggleTheme() {
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    theme.set(newTheme);
    localStorage.setItem('theme', newTheme);
  }

  const FONT_SIZES = [
    { label: 'S', scale: 0.85 },
    { label: 'M', scale: 1.0 },
    { label: 'L', scale: 1.15 },
    { label: 'XL', scale: 1.3 },
  ];
  let fontIdx = parseInt(localStorage.getItem('impro_font_idx') || '1');
  let currentFontSize = FONT_SIZES[fontIdx]?.label || 'M';
  let fontScale = FONT_SIZES[fontIdx]?.scale || 1;

  function applyFontScale() {
    fontScale = FONT_SIZES[fontIdx]?.scale || 1;
  }

  function cycleFontSize() {
    fontIdx = (fontIdx + 1) % FONT_SIZES.length;
    currentFontSize = FONT_SIZES[fontIdx].label;
    localStorage.setItem('impro_font_idx', String(fontIdx));
    applyFontScale();
  }

  if (typeof document !== 'undefined') {
    applyFontScale();
  }

  function handleLogout() {
    if (confirm('Sign out?')) {
      localStorage.removeItem('user');
      localStorage.removeItem('roogleCredentials');
      window.location.reload();
    }
  }

  function forgetRoogleCredentials() {
    if (confirm('Forget saved Roogle credentials?')) {
      localStorage.removeItem('roogleCredentials');
      alert('✅ Credentials cleared. You\'ll need to enter them again next time.');
    }
  }
</script>

<div class="main" data-theme={currentTheme} style="zoom: {fontScale}; -moz-transform: scale({fontScale}); -moz-transform-origin: top left;"
  on:touchstart|passive={(e) => {
    const x = e.touches[0].clientX;
    if (x < 30) { _appEdgeSwipe = true; _appEdgeStartX = x; _appEdgeDX = 0; }
  }}
  on:touchmove|passive={(e) => {
    if (!_appEdgeSwipe) return;
    _appEdgeDX = e.touches[0].clientX - _appEdgeStartX;
  }}
  on:touchend={() => {
    if (_appEdgeSwipe && _appEdgeDX > 80) {
      document.dispatchEvent(new CustomEvent('edge-swipe-back'));
    }
    _appEdgeSwipe = false; _appEdgeDX = 0;
  }}>
  <!-- Header -->
  <header class="header">
    <div class="header-top">
      <div class="header-logo-wrapper">
        <div class="logo-backdrop">
          <img src="{import.meta.env.BASE_URL}logo.png?v=2" alt="IndoorMedia" class="header-logo-img" />
        </div>
        <div class="header-text">
          <h1 class="portal-title">imPro</h1>
          <p class="portal-subtitle">Hi, {($user?.name || $user?.first_name || '').split(' ')[0]}</p>
        </div>
      </div>

      <div class="header-actions">
        <button class="header-icon-btn" on:click={() => currentTab = 'cart'} title="Cart">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/></svg>
          {#if cartCount > 0}
            <span class="cart-badge">{cartCount}</span>
          {/if}
        </button>
        <button class="header-icon-btn" on:click={toggleTheme} title="Toggle theme">
          {#if currentTheme === 'light'}
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
          {:else}
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>
          {/if}
        </button>
        <button class="header-icon-btn font-size-btn" on:click={cycleFontSize} title="Font size: {currentFontSize}">
          <span class="font-size-label">{currentFontSize}</span>
        </button>
        <button class="header-logout-btn" on:click={handleLogout}>Log Out</button>
      </div>
    </div>
  </header>

  <!-- Tab Bar (fixed bottom) -->
  <nav class="tab-bar">
    <button class="tab-bar-item" class:active={currentTab === 'stores'} on:click={() => currentTab = 'stores'}>
      <div class="tab-bar-indicator"></div>
      <svg class="tab-bar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/></svg>
      <span class="tab-bar-label">Stores</span>
    </button>
    <button class="tab-bar-item" class:active={currentTab === 'present'} on:click={() => currentTab = 'present'}>
      <div class="tab-bar-indicator"></div>
      <svg class="tab-bar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
      <span class="tab-bar-label">Present</span>
    </button>
    <button class="tab-bar-item tab-home" class:active={currentTab === 'dashboard'} on:click={() => currentTab = 'dashboard'}>
      <div class="tab-bar-indicator"></div>
      <svg class="tab-bar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
      <span class="tab-bar-label">Home</span>
    </button>
    <button class="tab-bar-item" class:active={currentTab === 'clients'} on:click={() => currentTab = 'clients'}>
      <div class="tab-bar-indicator"></div>
      <svg class="tab-bar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
      <span class="tab-bar-label">Clients</span>
    </button>
    <button class="tab-bar-item" class:active={currentTab === 'tools'} on:click={() => currentTab = 'tools'}>
      <div class="tab-bar-indicator"></div>
      <svg class="tab-bar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>
      <span class="tab-bar-label">Tools</span>
    </button>
  </nav>

  <!-- Content -->
  <div class="content">
    {#if currentTab === 'dashboard'}
      <div class="dashboard">
        <!-- 1. MOTIVATIONAL QUOTE — start the day right -->
        {#if true}
          {@const quote = getTodaysQuote()}
          <!-- svelte-ignore a11y-no-static-element-interactions -->
          <div class="quote-card"
            on:touchstart|preventDefault={(e) => {
              pressStart = Date.now();
              copyTimer = setTimeout(() => {
                copyQuoteText(`"${quote.text}" — ${quote.author}`);
              }, 500);
            }}
            on:touchend={() => { clearTimeout(copyTimer); }}
            on:touchmove={() => { clearTimeout(copyTimer); }}
            on:mousedown={() => {
              pressStart = Date.now();
              copyTimer = setTimeout(() => {
                copyQuoteText(`"${quote.text}" — ${quote.author}`);
              }, 500);
            }}
            on:mouseup={() => { clearTimeout(copyTimer); }}
            on:mouseleave={() => { clearTimeout(copyTimer); }}
            on:contextmenu|preventDefault
          >
            {#if quoteCopied}
              <p class="quote-copied-toast">✅ Copied to clipboard!</p>
            {:else}
              <p class="quote-text">"{quote.text}"</p>
              <p class="quote-author">— {quote.author}</p>
              <p class="quote-hint">Hold to copy</p>
            {/if}
          </div>
        {/if}

        <!-- 2. GREETING + QUICK ACTIONS — the "cockpit" -->
        <div class="hero-greeting">
          <h2 class="greeting-text">{new Date().getHours() < 12 ? 'Good morning' : new Date().getHours() < 17 ? 'Good afternoon' : 'Good evening'}, {($user?.name || $user?.first_name || '').split(' ')[0]}!</h2>
          {#if nextInstallCycle}
            <p class="cycle-pill">📦 {currentSellingCycle} Selling · {secondInstallCycle} installs {secondInstallDate} ({secondInstallDays}d)</p>
          {/if}
        </div>

        <div class="quick-actions-top">
          <button class="qa-btn qa-primary" on:click={() => { storesView = 'prospects'; currentTab = 'stores'; }}>
            <span class="qa-icon">🎯</span>
            <span class="qa-label">Find Prospects</span>
          </button>
          <button class="qa-btn" on:click={() => currentTab = 'stores'}>
            <span class="qa-icon">🏪</span>
            <span class="qa-label">Stores</span>
          </button>
          <button class="qa-btn" on:click={() => bookAppointment()}>
            <span class="qa-icon">📅</span>
            <span class="qa-label">Book Appt</span>
          </button>
          <button class="qa-btn qa-driving" on:click={() => showDrivingMode = true}>
            <span class="qa-icon">🚗</span>
            <span class="qa-label">Drive Mode</span>
          </button>
        </div>

        <!-- 2. TODAY AT A GLANCE — next appointment -->
        <button class="today-card-full" on:click={() => { showAppointmentsDetail = !showAppointmentsDetail; showStreakDetail = false; }}>
          <div class="today-icon">📅</div>
          {#if upcomingAppointments.length > 0}
            {@const next = upcomingAppointments[0]}
            <div class="today-info">
              <span class="today-title">{next.title || 'Appointment'}</span>
              <span class="today-meta">{new Date(next.date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })} · {new Date(next.date).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}</span>
            </div>
            {#if upcomingAppointments.length > 1}
              <span class="today-extra">+{upcomingAppointments.length - 1}</span>
            {/if}
          {:else}
            <div class="today-info">
              <span class="today-title">No appointments</span>
              <span class="today-meta">Tap to view or book</span>
            </div>
          {/if}
        </button>

        {#if showAppointmentsDetail}
          <div class="drill-down" style="border-top: 3px solid #CC0000; margin-top: 8px;">
            <h4>📅 Upcoming Appointments</h4>
            
            {#if upcomingAppointments.length > 0}
              <div class="appointment-list">
                {#each upcomingAppointments as appt, idx}
                  <div class="appointment-item swipeable" 
                       on:touchstart={(e) => handleSwipeStart(e, idx)}
                       on:touchend={(e) => handleSwipeEnd(e, idx)}
                       on:click={() => openInCalendar(appt)}
                       style="opacity: {swipingIndex === idx ? 0.7 : 1}; cursor: pointer;">
                    <div class="appt-left">
                      <div class="appt-date">{new Date(appt.date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}</div>
                      <div class="appt-time">{new Date(appt.date).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}</div>
                    </div>
                    <div class="appt-right">
                      <div class="appt-title">{appt.title || 'Appointment'}</div>
                      {#if appt.location}
                        <div class="appt-location">📍 {appt.location}</div>
                      {/if}
                      {#if appt.attendees?.length > 0}
                        <div class="appt-attendees">👥 {appt.attendees.map(a => a.name || a.email.split('@')[0]).join(', ')}</div>
                      {/if}
                      {#if appt.type === 'prospect'}
                        <span class="appt-badge prospect">Prospect Visit</span>
                      {/if}
                    </div>
                    <div class="appt-swipe-hint">← swipe to delete</div>
                  </div>
                {/each}
              </div>
            {:else}
              <p class="no-appointments">No upcoming appointments yet.</p>
            {/if}
            <button class="book-appt-btn" on:click={() => bookAppointment()}>📅 Book New Appointment</button>
            <div class="sync-bar">
              <button class="sync-refresh-btn" on:click={refreshAppointments}>🔄 Sync Now</button>
              {#if syncStatus}<span class="sync-status">{syncStatus}</span>{/if}
            </div>
          </div>
        {/if}

        <!-- 3. REVENUE HERO — motivation -->
        <button class="revenue-hero clickable" on:click={() => showRevenueDetail = !showRevenueDetail}>
          <div class="revenue-amount">${repMonthlyRevenue.toLocaleString()}</div>
          <div class="revenue-label">Revenue This Month — tap for details</div>
          {#if growthPercent !== 0}
            <div class="growth-badge" class:positive={growthPercent > 0} class:negative={growthPercent < 0}>
              {growthPercent > 0 ? '↑' : '↓'} {Math.abs(growthPercent)}% vs last month
            </div>
          {/if}
          <div class="week-revenue">This Week: <strong>${thisWeekRevenue.toLocaleString()}</strong> ({thisWeekContracts.length} deal{thisWeekContracts.length !== 1 ? 's' : ''})</div>
          {#if leaderboardPosition > 0}
            <div class="leaderboard-badge">🏆 #{leaderboardPosition} of {leaderboardTotal} reps this month</div>
          {/if}
        </button>

        {#if showRevenueDetail}
          <div class="drill-down">
            <h4>📅 Weekly Breakdown</h4>
            <div class="week-breakdown">
              {#each weeklyBreakdown as week}
                <div class="week-row" class:current-week={week.isCurrent}>
                  <div class="week-label">
                    <span>{week.weekLabel}</span>
                    {#if week.isCurrent}<span class="current-badge">This Week</span>{/if}
                  </div>
                  <div class="week-stats">
                    <span class="week-deals">{week.count} deal{week.count !== 1 ? 's' : ''}</span>
                    <span class="week-amount">${week.revenue.toLocaleString()}</span>
                  </div>
                </div>
              {/each}
            </div>

            <h4 style="margin-top:16px;">💰 All Contracts This Month ({thisMonthContracts.length})</h4>
            {#if thisMonthContracts.length === 0}
              <p class="drill-empty">No contracts this month yet.</p>
            {:else}
              {#each thisMonthContracts.sort((a, b) => (b.total_amount || 0) - (a.total_amount || 0)) as c}
                <div class="drill-row">
                  <div class="drill-info">
                    <span class="drill-name">{c.business_name || 'Unknown'}</span>
                    <span class="drill-meta">{c.sales_rep || ''} • {c.store_name || ''}</span>
                  </div>
                  <span class="drill-amount">${(c.total_amount || 0).toLocaleString()}</span>
                </div>
              {/each}
            {/if}
          </div>
        {/if}

        <!-- 4. STATS GRID — Prospects, Streak, Renewals -->
        <div class="dashboard-grid">
          <button class="stat-card clickable" on:click={() => { showProspectDetail = !showProspectDetail; showStreakDetail = false; }}>
            <div class="stat-icon">🎯</div>
            <h3>Prospects</h3>
            <p class="stat-value">{prospectsThisWeek}</p>
            <p class="stat-label">This Week — tap for breakdown</p>
          </button>
          <button class="stat-card clickable" on:click={() => { showStreakDetail = !showStreakDetail; showProspectDetail = false; }}>
            <div class="stat-icon">🔥</div>
            <h3>Streak</h3>
            <p class="stat-value">{streak}</p>
            <p class="stat-label">{streak === 1 ? 'Day' : 'Days'} Active</p>
          </button>
        </div>

        {#if showProspectDetail}
          <div class="drill-down">
            <h4>🎯 Prospect Activity — This Week</h4>
            <div class="prospect-breakdown-grid">
              <div class="breakdown-card">
                <div class="breakdown-value">{prospectBreakdown.searches}</div>
                <div class="breakdown-label">🔍 Searches</div>
              </div>
              <div class="breakdown-card">
                <div class="breakdown-value">{prospectBreakdown.calls}</div>
                <div class="breakdown-label">📞 Calls</div>
              </div>
              <div class="breakdown-card">
                <div class="breakdown-value">{prospectBreakdown.saved}</div>
                <div class="breakdown-label">💾 Saved</div>
              </div>
            </div>

            {#if prospectBreakdown.callNames.length > 0}
              <h5 style="margin: 16px 0 8px;">📞 Recent Calls</h5>
              {#each prospectBreakdown.callNames as call}
                <div class="breakdown-row">
                  <span>{call.name || 'Unknown'}</span>
                  <span class="breakdown-date">{call.phone}</span>
                </div>
              {/each}
            {/if}

            {#if prospectBreakdown.savedNames.length > 0}
              <h5 style="margin: 16px 0 8px;">💾 Saved Prospects</h5>
              {#each prospectBreakdown.savedNames as prospect}
                <div class="breakdown-row">
                  <span>{prospect.name}</span>
                  <span class="breakdown-date">{new Date(prospect.date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}</span>
                </div>
              {/each}
            {/if}

            {#if prospectBreakdown.searchTerms.length > 0}
              <h5 style="margin: 16px 0 8px;">🔍 Searches</h5>
              {#each prospectBreakdown.searchTerms as search}
                <div class="breakdown-row">
                  <span>{search.category || 'Search'}{search.store ? ` @ ${search.store}` : ''}</span>
                  <span class="breakdown-date">{new Date(search.date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}</span>
                </div>
              {/each}
            {/if}

            <button class="drill-goto-btn" on:click={() => { storesView = 'prospects'; currentTab = 'stores'; }}>
              🎯 Go to Prospects →
            </button>
          </div>
        {/if}

        {#if showStreakDetail}
          <div class="drill-down">
            <h4>🔥 Activity History (Last 14 Days)</h4>
            {#if streakDays.length === 0}
              <p class="drill-empty">No activity recorded yet. Search prospects or make calls to build your streak!</p>
            {:else}
              {#each streakDays as day}
                <div class="drill-row">
                  <div class="drill-info">
                    <span class="drill-name">{new Date(day.date + 'T12:00:00').toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}</span>
                    <span class="drill-meta">{day.searches} search{day.searches !== 1 ? 'es' : ''} • {day.calls} call{day.calls !== 1 ? 's' : ''}</span>
                  </div>
                  <span class="drill-amount">{day.searches + day.calls} actions</span>
                </div>
              {/each}
            {/if}
          </div>
        {/if}

        <!-- SUMMER SALES CONTEST 🏆 -->
        <button class="summer-sales-hero clickable" on:click={() => showSummerSalesDetail = !showSummerSalesDetail}>
          <div class="summer-sales-header">
            <span class="summer-sales-icon">☀️🏆</span>
            <h3>Summer Sales Contest</h3>
            <span class="summer-sales-dates">May 27 – Sep 1</span>
          </div>
          <div class="summer-sales-leaderboard">
            {#each summerSalesData as entry, i}
              <div class="summer-sales-row" class:gold={i === 0} class:silver={i === 1} class:bronze={i === 2}>
                <span class="summer-rank">{i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : `#${i+1}`}</span>
                <span class="summer-rep">{entry.rep}</span>
                <span class="summer-points">{entry.points % 1 === 0 ? entry.points : entry.points.toFixed(1)} pts</span>
              </div>
            {/each}
            {#if summerSalesData.length === 0}
              <p class="summer-empty">No contracts in contest period yet</p>
            {/if}
          </div>
        </button>

        {#if showSummerSalesDetail}
          <div class="drill-down summer-detail">
            <h4>☀️ Summer Sales Details</h4>
            <p class="summer-rules">1 pt/deal • Paid in Full = +1 pt • Renewal tape = 0 pts • Company lead = ½ pt</p>
            {#each summerSalesData as entry, idx}
              <div class="summer-rep-section">
                <button class="summer-rep-header" on:click={() => { summerSalesData[idx].expanded = !summerSalesData[idx].expanded; summerSalesData = summerSalesData; }}>
                  <strong>{entry.rep}</strong>
                  <span>{entry.points % 1 === 0 ? entry.points : entry.points.toFixed(1)} pts ({entry.deals} deal{entry.deals !== 1 ? 's' : ''})</span>
                </button>
                {#if entry.expanded}
                  <div class="summer-rep-deals">
                    {#each entry.details as deal}
                      <div class="summer-deal-row">
                        <div class="summer-deal-info">
                          <span class="summer-deal-name">{deal.business || 'Unknown'}</span>
                          <span class="summer-deal-meta">{deal.product} {deal.note ? `• ${deal.note}` : ''}</span>
                        </div>
                        <div class="summer-deal-right">
                          <span class="summer-deal-pts" class:zero={deal.points === 0} class:half={deal.points === 0.5}>{deal.points} pt{deal.points !== 1 ? 's' : ''}</span>
                        </div>
                      </div>
                    {/each}
                  </div>
                {/if}
              </div>
            {/each}

            <!-- Manager: Tag Company Leads -->
            {#if ($user?.name || '').toLowerCase().includes('tyler') || $user?.role === 'manager' || $user?.role === 'admin'}
              <div class="company-lead-tagger">
                <h4>🏢 Tag Company Leads (half points)</h4>
                <p class="tagger-hint">Toggle contracts that were call-in/TM leads</p>
                {#each summerSalesData as entry}
                  {#each entry.details as deal}
                    {#if deal.points > 0}
                      <label class="company-lead-toggle">
                        <input type="checkbox" checked={deal.isCompanyLead} on:change={() => toggleCompanyLead(deal.contract_number)} />
                        <span>{deal.business} — {deal.rep || entry.rep} ({deal.contract_number})</span>
                      </label>
                    {/if}
                  {/each}
                {/each}
              </div>
            {/if}
          </div>
        {/if}

        <!-- 5. FULL DAILY GOAL — expandable -->
        <div class="goal-section">
          <div class="goal-card">
            <div class="goal-header-row">
              <h3 class="goal-title">📋 Daily Goal</h3>
              <div class="goal-count-inline">{dailyGoal.calls} / {dailyGoal.target || 20}</div>
            </div>
            <div class="goal-progress">
              <div class="goal-bar">
                <div class="goal-fill" style="width: {Math.min((dailyGoal.calls / (dailyGoal.target || 20)) * 100, 100)}%"></div>
              </div>
            </div>
            {#if dailyGoal.calls >= (dailyGoal.target || 20)}
              <p class="goal-achieved">🎉 Goal reached! Keep crushing it!</p>
            {:else if dailyGoal.calls >= (dailyGoal.target || 20) * 0.5}
              <p class="goal-halfway">💪 Halfway there! Keep pushing!</p>
            {/if}
            <div class="goal-actions">
              <button class="goal-btn increment" on:click={incrementCalls}>+ Log Call / Walk-in</button>
              <button class="goal-btn reset" on:click={resetDailyGoal}>↺ Reset</button>
              <div class="goal-target-set">
                <label>Goal:</label>
                <input type="number" value={dailyGoal.target || 20} on:change={(e) => setGoalTarget(e.target.value)} min="1" max="100" />
              </div>
            </div>
          </div>
        </div>


      </div>
    {:else if currentTab === 'stores'}
      <div class="stores-view-toggle">
        <button class="view-toggle-btn" class:active={storesView === 'rates'} on:click={() => storesView = 'rates'}>📊 Rates</button>
        <button class="view-toggle-btn" class:active={storesView === 'prospects'} on:click={() => storesView = 'prospects'}>🎯 Prospects</button>
        <button class="view-toggle-btn" class:active={storesView === 'map'} on:click={() => storesView = 'map'}>🗺️ Map</button>
      </div>
      {#if storesView === 'rates'}
        <StoreSearch />
      {:else if storesView === 'prospects'}
        <ProspectSearch />
      {:else}
        <StoreMap />
      {/if}
    {:else if currentTab === 'tools'}
      <Tools {contracts} />
    {:else if currentTab === 'cart'}
      <Cart />
    {:else if currentTab === 'products'}
      <Products />
    {:else if currentTab === 'present'}
      <Present />
    {:else if currentTab === 'clients'}
      <Clients />
    {:else if currentTab === 'addlead'}
      <HotLeadsSubmit
        user={$user}
        onLeadSubmitted={() => {
          // Optional: show confirmation or navigate back to prospects
          storesView = 'prospects'; currentTab = 'stores';
        }}
      />
    {:else if currentTab === 'manage'}
      <ManageReps />
    {/if}
  </div>

  {#if showDrivingMode}
    <DrivingMode
      appointments={upcomingAppointments}
      onClose={() => showDrivingMode = false}
    />
  {/if}
</div>

<style>
  :global(html) {
    background: #CC0000;
  }
  :global(body) {
    background: var(--bg-primary, #ffffff);
  }
  :global([data-theme='light']) {
    --bg-primary: #ffffff;
    --bg-secondary: #f9f9f9;
    --text-primary: #1a1a1a;
    --text-secondary: #666666;
    --text-tertiary: #999999;
    --border-color: #e0e0e0;
    --card-bg: #ffffff;
    --card-shadow: rgba(0, 0, 0, 0.08);
    --hover-bg: #f5f5f5;
    --input-bg: #ffffff;
  }

  :global([data-theme='dark']) {
    --bg-primary: #1a1a1a;
    --bg-secondary: #242424;
    --text-primary: #ffffff;
    --text-secondary: #aaaaaa;
    --text-tertiary: #777777;
    --border-color: #333333;
    --card-bg: #2a2a2a;
    --card-shadow: rgba(0, 0, 0, 0.3);
    --hover-bg: #333333;
    --input-bg: #2a2a2a;
  }

  .main {
    display: flex;
    flex-direction: column;
    height: 100%;
    background: var(--bg-primary);
    color: var(--text-primary);
  }

  /* Black status bar area (above header) on iOS */
  :global(html) {
    background: #000000;
  }
  :global(body) {
    background: var(--bg-primary, #f5f5f5);
  }

  /* Header */
  .header {
    background: linear-gradient(135deg, #1a1a1a 0%, #000000 100%);
    color: white;
    padding: 0;
    margin: 0;
    margin-left: calc(-1 * env(safe-area-inset-left));
    margin-right: calc(-1 * env(safe-area-inset-right));
    padding-top: calc(16px + env(safe-area-inset-top));
    padding-left: calc(20px + env(safe-area-inset-left));
    padding-right: calc(20px + env(safe-area-inset-right));
    padding-bottom: 16px;
    display: flex;
    flex-direction: column;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
  }

  .header-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0;
    gap: 8px;
    overflow: visible;
  }

  .header-logo-wrapper {
    display: flex;
    align-items: center;
    gap: 12px;
    flex: 1;
  }

  .logo-backdrop {
    width: 56px;
    height: 56px;
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    overflow: hidden;
  }

  .header-logo-img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .header-text {
    margin: 0;
  }

  .portal-title {
    margin: 0;
    font-size: 24px;
    font-weight: 800;
    letter-spacing: -0.5px;
    line-height: 1;
  }

  .portal-subtitle {
    margin: 2px 0 0;
    font-size: 11px;
    font-weight: 500;
    opacity: 0.85;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .header-bottom {
    padding: 0;
    text-align: left;
  }

  .user-greeting {
    margin: 0;
    font-size: 13px;
    opacity: 0.9;
  }

  .user-greeting strong {
    font-weight: 700;
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-shrink: 1;
    min-width: 0;
    overflow: visible;
  }

  .header-icon-btn {
    background: rgba(255, 255, 255, 0.15);
    border: none;
    color: white;
    cursor: pointer;
    position: relative;
    width: 36px;
    height: 36px;
    border-radius: 10px;
    transition: all 0.2s;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    flex-shrink: 0;
  }

  .header-icon-btn:hover {
    background: rgba(255, 255, 255, 0.25);
    transform: translateY(-1px);
  }

  .font-size-label { font-size: 14px; font-weight: 700; color: white; font-family: inherit; letter-spacing: -0.5px; }

  .header-icon-btn.logout-text {
    width: auto;
    padding: 0 14px;
    font-size: 13px;
    font-weight: 600;
    color: white;
    font-family: inherit;
  }

  .cart-badge {
    position: absolute;
    top: -4px;
    right: -6px;
    background: white;
    color: #CC0000;
    font-size: 11px;
    font-weight: 700;
    min-width: 18px;
    height: 18px;
    border-radius: 9px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  /* Tab Bar — fixed bottom */
  .tab-bar {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    z-index: 1000;
    background: linear-gradient(135deg, #CC0000 0%, #990000 100%);
    border-top: 3px solid #ff3333;
    box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.15);
    display: flex;
    align-items: flex-start;
    padding-bottom: env(safe-area-inset-bottom, 0px);
  }
  :global([data-theme='dark']) .tab-bar {
    background: linear-gradient(135deg, #990000 0%, #660000 100%);
    border-top: none;
    box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.3);
  }

  .tab-bar-item {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: flex-start;
    gap: 2px;
    background: none;
    border: none;
    color: rgba(255, 255, 255, 0.6);
    cursor: pointer;
    position: relative;
    padding: 10px 2px 10px;
    transition: color 0.2s;
    -webkit-tap-highlight-color: transparent;
  }

  .tab-bar-item:hover {
    color: rgba(255, 255, 255, 0.85);
  }

  .tab-bar-item.active {
    color: #ffffff;
  }

  .tab-bar-indicator {
    position: absolute;
    top: 4px;
    left: 50%;
    transform: translateX(-50%);
    width: 30px;
    height: 3px;
    border-radius: 3px;
    background: transparent;
    transition: background 0.2s;
  }

  .tab-bar-item.active .tab-bar-indicator {
    background: #ffffff;
  }

  .tab-bar-icon {
    width: 26px;
    height: 26px;
    stroke: currentColor;
    flex-shrink: 0;
  }



  .tab-bar-label {
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.2px;
    line-height: 1;
  }

  /* Content */
  .content {
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
    -webkit-overflow-scrolling: touch;
    padding: 20px 20px calc(140px + env(safe-area-inset-bottom, 0px));
    max-width: 1400px;
    margin: 0 auto;
    width: 100%;
    box-sizing: border-box;
  }
  .content :global(> *:last-child) {
    padding-bottom: 140px !important;
  }

  /* Dashboard */
  /* Motivational Quote */
  /* Hero Greeting */
  .hero-greeting { margin-bottom: 12px; }
  .greeting-text { font-size: 22px; font-weight: 700; margin: 0 0 4px; color: var(--text-primary); }
  .cycle-pill { font-size: 12px; color: var(--text-secondary); margin: 0; padding: 4px 10px; background: var(--card-bg, #f5f5f5); border-radius: 20px; display: inline-block; border: 1px solid var(--border-color, #e0e0e0); }

  /* Quick Actions Top Row */
  .quick-actions-top { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 16px; }
  .qa-btn {
    display: flex; flex-direction: column; align-items: center; gap: 4px;
    padding: 12px 6px; border-radius: 12px; border: 1px solid var(--border-color, #e0e0e0);
    background: var(--card-bg, #fff); cursor: pointer; transition: all 0.2s;
    color: var(--text-primary);
  }
  .qa-btn:active { transform: scale(0.96); }
  .qa-btn.qa-primary { background: #CC0000; color: white; border-color: #CC0000; }
  .qa-btn.qa-primary .qa-label { color: white; }
  .qa-icon { font-size: 22px; }
  .qa-label { font-size: 11px; font-weight: 600; text-align: center; line-height: 1.2; color: var(--text-secondary); }
  .qa-badge { background: #CC0000; color: white; font-size: 10px; padding: 1px 5px; border-radius: 8px; margin-left: 2px; }
  .qa-btn.qa-primary .qa-badge { background: white; color: #CC0000; }
  .qa-btn.qa-driving { background: #1a1a2e; color: #fff; border-color: #333; }
  .qa-btn.qa-driving .qa-label { color: #ccc; }

  /* Today at a Glance */
  .today-card-full {
    background: var(--card-bg, #fff); border-radius: 12px; padding: 12px 14px;
    border: 1px solid var(--border-color, #e0e0e0); display: flex; align-items: center; gap: 10px;
    cursor: pointer; transition: all 0.2s; color: var(--text-primary); width: 100%;
    margin-bottom: 16px; box-sizing: border-box; font-family: inherit;
  }
  .today-card-full:active { transform: scale(0.98); }
  .today-icon { font-size: 20px; flex-shrink: 0; }
  .today-info { display: flex; flex-direction: column; gap: 2px; min-width: 0; flex: 1; }
  .today-title { font-size: 13px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .today-meta { font-size: 11px; color: var(--text-secondary); }
  .today-extra { font-size: 11px; font-weight: 700; color: #CC0000; flex-shrink: 0; }

  /* Goal section improvements */
  .goal-header-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
  .goal-title { margin: 0; font-size: 16px; }
  .goal-count-inline { font-size: 18px; font-weight: 700; color: #CC0000; }

  .quote-card {
    background: linear-gradient(135deg, #CC0000, #8B0000);
    color: white;
    padding: 16px 20px;
    border-radius: 12px;
    margin-bottom: 16px;
    text-align: center;
  }
  .quote-text { font-size: 15px; font-style: italic; line-height: 1.4; margin: 0 0 6px; }
  .quote-author { font-size: 12px; opacity: 0.85; margin: 0; }
  .quote-hint { font-size: 10px; opacity: 0.5; margin: 4px 0 0; }
  .quote-copied-toast { font-size: 15px; margin: 0; padding: 4px 0; }
  .quote-card { cursor: pointer; -webkit-user-select: none; user-select: none; -webkit-touch-callout: none; }

  /* Revenue Hero */
  .revenue-hero {
    background: var(--bg-secondary, #1a1a2e);
    border: 2px solid #CC0000;
    border-radius: 12px;
    padding: 20px;
    text-align: center;
    margin-bottom: 16px;
  }
  .revenue-amount { font-size: 36px; font-weight: 800; color: #CC0000; }
  .revenue-label { font-size: 13px; color: var(--text-secondary, #999); margin-top: 2px; }
  .week-revenue { font-size: 14px; color: var(--text-secondary, #999); margin-top: 6px; }
  .week-revenue strong { color: var(--text-primary, #333); }
  .week-breakdown { margin-bottom: 16px; }
  .week-row { display: flex; justify-content: space-between; align-items: center; padding: 10px 12px; border-radius: 8px; margin-bottom: 4px; background: var(--bg-secondary, #f9f9f9); }
  .week-row.current-week { background: #FFF3E0; border: 1px solid #E65100; }
  .week-label { display: flex; align-items: center; gap: 6px; font-size: 13px; color: var(--text-primary); }
  .current-badge { font-size: 10px; padding: 2px 6px; background: #E65100; color: white; border-radius: 4px; font-weight: 700; }
  .week-stats { display: flex; gap: 12px; align-items: center; }
  .week-deals { font-size: 12px; color: var(--text-secondary, #888); }
  .week-amount { font-size: 15px; font-weight: 800; color: #2E7D32; }
  .growth-badge { display: inline-block; margin-top: 8px; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; }
  .growth-badge.positive { background: #e8f5e9; color: #2e7d32; }
  .growth-badge.negative { background: #ffe0e0; color: #c33; }
  .leaderboard-badge { margin-top: 6px; font-size: 13px; color: var(--text-secondary, #aaa); }

  /* Daily Goal */
  .goal-section { margin-bottom: 16px; }
  .goal-section h3 { margin: 0 0 8px; font-size: 17px; font-weight: 700; color: var(--text-primary); }
  .goal-card {
    background: var(--card-bg, #ffffff);
    border-radius: 12px;
    padding: 16px;
    border: 1px solid #e8e8e8;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  }
  :global([data-theme='dark']) .goal-card {
    background: #1e1e1e;
    border-color: #333;
  }
  .goal-progress { margin-bottom: 8px; }
  .goal-bar { height: 12px; background: #333; border-radius: 6px; overflow: hidden; }
  .goal-fill { height: 100%; background: linear-gradient(90deg, #CC0000, #ff4444); border-radius: 6px; transition: width 0.3s; }
  .goal-count { text-align: center; font-size: 24px; font-weight: 700; color: var(--text-primary); margin-top: 8px; }
  .goal-label { text-align: center; font-size: 13px; color: var(--text-secondary, #999); margin: 4px 0 12px; }
  .goal-actions { display: flex; gap: 8px; align-items: center; }
  .goal-btn.increment {
    flex: 1;
    padding: 12px;
    background: #CC0000;
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 15px;
    font-weight: 600;
    cursor: pointer;
  }
  .goal-btn.increment:active { transform: scale(0.97); }
  .goal-target-set { display: flex; align-items: center; gap: 6px; }
  .goal-target-set label { font-size: 13px; color: var(--text-secondary, #999); }
  .goal-target-set input { width: 50px; padding: 8px; border: 1px solid var(--border-color, #333); border-radius: 6px; font-size: 14px; text-align: center; background: var(--bg-primary, #111); color: var(--text-primary); }
  .goal-achieved { text-align: center; margin-top: 10px; font-size: 14px; color: #2e7d32; font-weight: 600; }
  .goal-halfway { text-align: center; margin-top: 10px; font-size: 13px; color: #ff9800; }

  /* Appointments */
  .appointments-section { margin-bottom: 16px; }
  .appointments-section h3 { margin: 0 0 12px; font-size: 16px; color: var(--text-primary); }
  .appointment-list { display: flex; flex-direction: column; gap: 12px; }
  .appointment-item {
    display: flex;
    align-items: flex-start;
    gap: 14px;
    background: var(--card-bg);
    border-radius: 12px;
    padding: 16px;
    border: 2px solid var(--border-color);
    transition: border-color 0.2s;
    position: relative;
  }
  .appointment-item:hover { border-color: #CC0000; background: rgba(204, 0, 0, 0.02); }
  .appointment-item.swipeable { touch-action: pan-y; user-select: none; transition: opacity 0.15s; }
  .appt-swipe-hint { position: absolute; right: 16px; top: 50%; transform: translateY(-50%); font-size: 11px; color: rgba(204, 0, 0, 0.5); white-space: nowrap; opacity: 0; transition: opacity 0.2s; }
  .appointment-item:hover .appt-swipe-hint { opacity: 1; }
  .appt-left { min-width: 85px; flex-shrink: 0; text-align: center; background: rgba(204,0,0,0.05); border-radius: 8px; padding: 8px 4px; }
  .appt-date { font-size: 14px; font-weight: 800; color: #CC0000; white-space: nowrap; }
  .appt-time { font-size: 13px; color: var(--text-tertiary); margin-top: 4px; font-weight: 600; }
  .appt-right { flex: 1; }
  .appt-title { font-size: 16px; font-weight: 700; color: var(--text-primary); margin-bottom: 6px; }
  .appt-location { font-size: 13px; color: var(--text-secondary); margin-bottom: 4px; }
  .appt-attendees { font-size: 13px; color: var(--text-tertiary); margin-bottom: 6px; }
  .appt-badge { display: inline-block; font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 6px; }
  .appt-badge.prospect { background: rgba(204,0,0,0.1); color: #CC0000; }
  .no-appointments { font-size: 13px; color: var(--text-secondary); text-align: center; padding: 12px; }
  .book-appt-btn { width: 100%; padding: 10px; margin-top: 12px; background: #CC0000; color: white; border: none; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; }
  .book-appt-btn:hover { background: #aa0000; }
  .sync-bar { display: flex; align-items: center; gap: 8px; margin-top: 10px; justify-content: center; }
  .sync-refresh-btn { padding: 6px 14px; background: var(--bg-secondary, #f0f0f0); border: 1px solid var(--border-color, #ddd); border-radius: 6px; font-size: 13px; cursor: pointer; color: var(--text-primary); }
  .sync-refresh-btn:hover { background: var(--border-color, #ddd); }
  .sync-status { font-size: 12px; color: var(--text-secondary, #666); }
  .sync-btn { position: absolute; top: 6px; right: 6px; background: none; border: none; font-size: 16px; cursor: pointer; padding: 2px; opacity: 0.6; }
  .sync-btn:hover { opacity: 1; }
  .stat-card { position: relative; }
  .sync-note { font-size: 11px; color: var(--text-muted, #999); text-align: center; margin-top: 8px; }

  /* Cycle Countdown */
  .cycle-card .cycle-info { margin-top: 8px; }
  .cycle-card .cycle-line { margin: 0; font-size: 13px; color: var(--text-secondary); }
  .cycle-card .cycle-line strong { color: #CC0000; }
  .cycle-card .cycle-days-label { margin: 0 0 8px; font-size: 12px; color: var(--text-tertiary); }
  .cycle-columns { display: flex; gap: 0; margin-top: 8px; }
  .cycle-col { flex: 1; text-align: center; }
  .cycle-col-title { font-size: 11px; font-weight: 700; color: #CC0000; letter-spacing: 1px; margin: 0 0 6px; }
  .cycle-divider { width: 1px; background: #e0e0e0; margin: 0 8px; }

  .header-logout-btn {
    background: rgba(255,255,255,0.15);
    border: 1px solid rgba(255,255,255,0.3);
    color: rgba(255,255,255,0.8);
    padding: 6px 8px;
    border-radius: 8px;
    font-size: 10px;
    font-weight: 600;
    cursor: pointer;
    margin: 0;
    white-space: nowrap;
    flex-shrink: 0;
  }
  .header-logout-btn:hover { background: rgba(255,255,255,0.3); }

  /* Clickable cards */
  .clickable { cursor: pointer; transition: transform 0.15s, box-shadow 0.15s; }
  .clickable:active { transform: scale(0.97); }
  .revenue-hero.clickable { border: none; width: 100%; text-align: center; font-family: inherit; }

  /* Drill-down panels */
  .drill-down {
    background: var(--card-bg);
    border: 2px solid var(--border-color);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 20px;
    margin-top: 16px;
  }
  .drill-down h4 { margin: 0 0 16px; font-size: 17px; font-weight: 700; color: var(--text-primary); }
  .drill-down h5 { font-size: 14px; font-weight: 700; color: var(--text-secondary); }

  .prospect-breakdown-grid {
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 16px;
  }
  .breakdown-card {
    background: var(--bg-secondary, #f9f9f9); border-radius: 10px; padding: 14px 8px; text-align: center;
    border: 1px solid var(--border-color, #eee);
  }
  .breakdown-value { font-size: 28px; font-weight: 800; color: #CC0000; }
  .breakdown-label { font-size: 12px; color: var(--text-secondary); font-weight: 600; margin-top: 4px; }
  .breakdown-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 8px 0; border-bottom: 1px solid var(--border-color, #eee); font-size: 13px;
  }
  .breakdown-date { font-size: 11px; color: var(--text-tertiary, #999); }
  .drill-goto-btn {
    display: block; width: 100%; margin-top: 16px; padding: 14px;
    background: #CC0000; color: white; border: none; border-radius: 12px;
    font-size: 16px; font-weight: 700; cursor: pointer; text-align: center;
  }
  .drill-empty { font-size: 13px; color: var(--text-secondary, #999); text-align: center; padding: 8px; }
  .drill-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 10px;
    background: var(--bg-primary, #111);
    border-radius: 8px;
    margin-bottom: 4px;
  }
  .drill-info { display: flex; flex-direction: column; }
  .drill-name { font-size: 14px; font-weight: 600; color: var(--text-primary); }
  .drill-meta { font-size: 12px; color: var(--text-secondary, #999); }
  .drill-amount { font-size: 14px; font-weight: 700; color: #2e7d32; white-space: nowrap; }

  /* Reset button */
  .goal-btn.reset {
    padding: 12px 14px;
    background: #555;
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
  }
  .goal-btn.reset:active { background: #333; }

  .dashboard {
    max-width: 100%;
    margin: 0 auto;
    width: 100%;
    padding-bottom: 140px;
  }

  .dashboard h2 {
    margin: 0 0 8px;
    color: var(--text-primary);
    font-size: 22px;
    font-weight: 700;
  }

  .location-badge {
    margin: 0 0 24px;
    padding: 8px 12px;
    background: rgba(204, 0, 0, 0.1);
    color: #CC0000;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 600;
    display: inline-block;
  }

  .dashboard-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
    margin-bottom: 32px;
    width: 100%;
  }

  @media (min-width: 768px) {
    .dashboard-grid {
      grid-template-columns: repeat(3, 1fr);
      gap: 2rem;
    }
  }

  @media (min-width: 1200px) {
    .dashboard-grid {
      grid-template-columns: repeat(4, 1fr);
      gap: 2rem;
    }
  }

  .stat-card {
    background: var(--card-bg, #ffffff);
    border-radius: 12px;
    border: 1px solid #e8e8e8;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
    padding: 1.5rem 1.25rem;
    text-align: center;
    min-height: 180px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    width: 100%;
    transition: transform 0.15s, box-shadow 0.2s;
  }
  :global([data-theme='dark']) .stat-card {
    background: #1e1e1e;
    border-color: #333;
  }

  .stat-card.clickable { cursor: pointer; }
  .stat-card.clickable:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
  .stat-card.clickable:active { transform: scale(0.98); }

  .stat-icon {
    font-size: 36px;
    margin-bottom: 10px;
  }

  .stat-card h3 {
    margin: 0 0 10px;
    font-size: 13px;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-weight: 500;
  }

  .stat-value {
    margin: 0 0 6px;
    font-size: 32px;
    font-weight: 800;
    color: #CC0000;
    line-height: 1.1;
  }

  .stat-label {
    margin: 0;
    font-size: 13px;
    color: var(--text-tertiary);
    font-weight: 500;
  }

  .quick-actions {
    margin-top: 32px;
  }

  .quick-actions h3 {
    margin: 0 0 16px;
    color: var(--text-primary);
    font-size: 17px;
    font-weight: 700;
  }

  .action-buttons {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 1.5rem;
    width: 100%;
  }

  @media (min-width: 768px) {
    .action-buttons {
      grid-template-columns: repeat(3, 1fr);
      gap: 2rem;
    }
  }

  @media (min-width: 1200px) {
    .action-buttons {
      grid-template-columns: repeat(4, 1fr);
      gap: 2rem;
    }
  }

  .action-btn {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    padding: 16px;
    background: var(--card-bg, #ffffff);
    border: 1px solid #e8e8e8;
    border-radius: 12px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
    cursor: pointer;
    transition: all 0.2s;
    color: var(--text-primary);
    font-weight: 600;
    font-size: 13px;
  }
  :global([data-theme='dark']) .action-btn {
    background: #1e1e1e;
    border-color: #333;
  }

  .action-btn:hover {
    border-color: #CC0000;
    background: rgba(204, 0, 0, 0.05);
  }

  .action-icon {
    font-size: 24px;
  }

  @media (max-width: 768px) {
    .header-logo-section {
      padding: 32px 16px 16px;
    }

    .header-bottom {
      padding: 10px 16px 16px;
      flex-direction: column;
      align-items: flex-start;
    }

    .header-info h1 {
      font-size: 20px;
    }

    .content {
      padding: 16px;
    }

    .dashboard-grid {
      grid-template-columns: repeat(2, 1fr);
      gap: 14px;
    }

    .stat-card {
      min-height: 200px;
      padding: 1.75rem 1rem;
    }

    .stat-icon {
      font-size: 42px;
    }

    .stat-value {
      font-size: 36px;
    }

    .action-buttons {
      grid-template-columns: repeat(2, 1fr);
    }
  }

  @media (max-width: 480px) {
    .header-logo-section {
      padding: 24px 12px 12px;
    }

    .header-logo-svg {
      max-width: 280px;
    }

    .header-bottom {
      padding: 8px 12px 12px;
    }

    .header-info h1 {
      font-size: 18px;
    }

    .tabs {
      padding: 0;
    }

    .tab {
      padding: 10px 12px;
      font-size: 12px;
    }

    .dashboard h2 {
      font-size: 22px;
    }

    .dashboard-grid, .action-buttons {
      grid-template-columns: 1fr;
    }
  }
  /* Analytics */
  .analytics-container { padding: 16px; padding-bottom: 140px; max-width: 100%; margin: 0 auto; width: 100%; }
  .period-selector { display: flex; gap: 8px; margin-bottom: 12px; }
  .zone-filter { display: flex; align-items: center; gap: 6px; margin-bottom: 16px; overflow-x: auto; white-space: nowrap; padding-bottom: 4px; }
  .zone-label { font-size: 12px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; flex-shrink: 0; }
  .zone-btn { padding: 5px 12px; border: 1px solid var(--border-color); border-radius: 16px; background: var(--card-bg); font-size: 12px; font-weight: 600; cursor: pointer; color: var(--text-secondary); transition: all 0.2s; flex-shrink: 0; }
  .zone-btn.active { background: #1a237e; color: white; border-color: #1a237e; }
  .zone-btn:hover:not(.active) { border-color: #1a237e; color: #1a237e; }
  .zone-active-label { font-size: 13px; color: #1a237e; font-weight: 600; margin-bottom: 16px; }
  .period-btn { padding: 8px 16px; border: 1px solid var(--border-color); border-radius: 20px; background: var(--card-bg); color: var(--text-secondary); font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.2s; }
  .period-btn.active { background: #CC0000; color: white; border-color: #CC0000; }
  .analytics-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 16px; }
  .analytics-card { background: var(--card-bg, #ffffff); border: 1px solid #e8e8e8; border-radius: 12px; padding: 16px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.06); transition: box-shadow 0.2s; }
  .analytics-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
  :global([data-theme='dark']) .analytics-card { background: #1e1e1e; border-color: #333; }
  .analytics-year { font-size: 18px; font-weight: 700; color: var(--text-primary); margin-bottom: 8px; }
  .analytics-amount { font-size: 28px; font-weight: 800; color: #CC0000; margin-bottom: 4px; }
  .analytics-count { font-size: 12px; color: var(--text-secondary); margin-bottom: 8px; }
  .analytics-change { font-size: 14px; font-weight: 600; padding: 4px 8px; border-radius: 8px; display: inline-block; }
  .analytics-change.positive { background: #e8f5e9; color: #2e7d32; }
  .analytics-change.negative { background: #ffebee; color: #c62828; }
  
  /* App Usage / Activity */
  .activity-section h3 { font-size: 17px; font-weight: 700; margin-bottom: 8px; color: var(--text-primary); }
  .activity-section h4 { font-size: 15px; font-weight: 600; margin: 20px 0 10px; color: var(--text-primary); }
  .activity-note { font-size: 12px; color: var(--text-secondary); margin-bottom: 16px; }
  .activity-summary { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-bottom: 20px; }
  .activity-card { background: var(--card-bg, #ffffff); border: 1px solid #e8e8e8; border-radius: 12px; padding: 16px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
  :global([data-theme='dark']) .activity-card { background: #1e1e1e; border-color: #333; }
  .activity-icon { font-size: 28px; margin-bottom: 6px; }
  .activity-stat { font-size: 28px; font-weight: 800; color: #CC0000; }
  .activity-label { font-size: 12px; color: var(--text-secondary); font-weight: 600; margin-top: 4px; }
  .activity-table-wrap { overflow-x: auto; }
  .activity-table { width: 100%; border-collapse: collapse; font-size: 13px; }
  .activity-table th { background: var(--bg-secondary, #f5f5f5); padding: 8px 10px; text-align: left; font-weight: 700; color: var(--text-secondary); border-bottom: 2px solid var(--border-color); }
  .activity-table td { padding: 8px 10px; border-bottom: 1px solid var(--border-color); color: var(--text-primary); }
  .activity-totals { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; font-size: 14px; color: var(--text-primary); }
  .activity-totals strong { color: var(--text-secondary); }
  .deals-summary { margin-bottom: 12px; }
  .deals-total { text-align: center; padding: 14px; background: #E8F5E9; border-radius: 10px; border: 1px solid #2E7D32; }
  .deals-total-value { font-size: 24px; font-weight: 800; color: #2E7D32; display: block; }
  .deals-total-label { font-size: 12px; color: #2E7D32; font-weight: 600; }
  .deal-detail-row { background: var(--bg-secondary, #f9f9f9) !important; }
  .profit { color: #2E7D32; font-weight: 700; }
  .firebase-setup-prompt { background: var(--card-bg); border: 2px dashed var(--border-color); border-radius: 12px; padding: 20px; text-align: center; margin: 16px 0; }
  .firebase-setup-prompt h4 { margin: 0 0 8px; color: var(--text-primary); }
  .firebase-setup-prompt p { font-size: 13px; color: var(--text-secondary); margin: 0 0 12px; }
  .month-table, .rep-table { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 12px; overflow: hidden; }
  .month-table table, .rep-table table { width: 100%; border-collapse: collapse; }
  .month-table th, .rep-table th { background: var(--bg-secondary); padding: 12px; text-align: left; font-weight: 700; font-size: 12px; color: var(--text-secondary); text-transform: uppercase; border-bottom: 1px solid var(--border-color); }
  .month-table td, .rep-table td { padding: 12px; border-bottom: 1px solid var(--border-color); color: var(--text-primary); }
  .month-table tr:last-child td, .rep-table tr:last-child td { border-bottom: none; }
  .month-table tr:hover, .rep-table tr:hover { background: var(--bg-secondary); }

  /* Stores view toggle */
  .stores-view-toggle {
    display: flex;
    gap: 8px;
    margin-bottom: 12px;
  }
  .view-toggle-btn {
    padding: 8px 20px;
    border: 1px solid var(--border-color, #ddd);
    border-radius: 20px;
    background: var(--card-bg, #fff);
    color: var(--text-secondary, #666);
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
  }
  .view-toggle-btn.active {
    background: #CC0000;
    color: white;
    border-color: #CC0000;
  }
  .view-toggle-btn:hover:not(.active) {
    border-color: #CC0000;
    color: #CC0000;
  }

  /* Summer Sales Contest */
  .summer-sales-hero {
    background: linear-gradient(135deg, #ff6b35, #f7c948);
    border-radius: 20px;
    padding: 20px;
    margin: 16px 0;
    color: #fff;
    text-align: left;
    width: 100%;
    border: none;
    font-family: inherit;
    cursor: pointer;
  }
  :global([data-theme='dark']) .summer-sales-hero {
    background: linear-gradient(135deg, #c44d1a, #b8941f);
  }
  .summer-sales-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 16px;
  }
  .summer-sales-header h3 {
    margin: 0;
    font-size: 20px;
    font-weight: 800;
    flex: 1;
  }
  .summer-sales-icon { font-size: 28px; }
  .summer-sales-dates {
    font-size: 12px;
    opacity: 0.8;
    background: rgba(255,255,255,0.2);
    padding: 4px 10px;
    border-radius: 12px;
  }
  .summer-sales-leaderboard {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .summer-sales-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 6px 10px;
    border-radius: 10px;
    background: rgba(255,255,255,0.1);
  }
  .summer-sales-row.gold { background: rgba(255,255,255,0.25); font-weight: 700; }
  .summer-sales-row.silver { background: rgba(255,255,255,0.18); }
  .summer-sales-row.bronze { background: rgba(255,255,255,0.13); }
  .summer-rank { font-size: 18px; min-width: 30px; text-align: center; }
  .summer-rep { flex: 1; font-size: 15px; }
  .summer-points { font-weight: 700; font-size: 16px; }
  .summer-empty { text-align: center; opacity: 0.7; font-style: italic; }

  .summer-detail .summer-rules {
    font-size: 12px;
    color: var(--text-secondary);
    margin: -8px 0 16px;
    font-style: italic;
  }
  .summer-rep-section {
    margin-bottom: 12px;
    border: 1px solid var(--border-color, #eee);
    border-radius: 12px;
    overflow: hidden;
  }
  .summer-rep-header {
    display: flex;
    justify-content: space-between;
    padding: 12px 16px;
    cursor: pointer;
    background: var(--bg-secondary, #f5f5f5);
    border: none;
    width: 100%;
    font-family: inherit;
    font-size: inherit;
    color: var(--text-primary);
  }
  .summer-rep-header:hover { opacity: 0.8; }
  .summer-rep-deals { padding: 8px 16px; }
  .summer-deal-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 6px 0;
    border-bottom: 1px solid var(--border-color, #eee);
  }
  .summer-deal-row:last-child { border-bottom: none; }
  .summer-deal-name { font-size: 14px; font-weight: 500; }
  .summer-deal-meta { font-size: 12px; color: var(--text-secondary); display: block; }
  .summer-deal-pts { font-weight: 700; font-size: 14px; }
  .summer-deal-pts.zero { color: #999; }
  .summer-deal-pts.half { color: #e67e22; }

  .company-lead-tagger {
    margin-top: 20px;
    padding-top: 16px;
    border-top: 2px solid var(--border-color, #eee);
  }
  .company-lead-tagger h4 { margin: 0 0 4px; }
  .tagger-hint { font-size: 12px; color: var(--text-secondary); margin-bottom: 12px; }
  .company-lead-toggle {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 6px 0;
    font-size: 14px;
    cursor: pointer;
  }
  .company-lead-toggle input { width: 18px; height: 18px; }
</style>
