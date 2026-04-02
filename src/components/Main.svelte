<script>
  import { onMount } from 'svelte';
  import { theme, user } from '../lib/stores.js';
  import { get } from 'svelte/store';
  import StoreSearch from './StoreSearch.svelte';
  import ProspectSearch from './ProspectSearch.svelte';
  import Tools from './Tools.svelte';
  import Cart from './Cart.svelte';
  import Products from './Products.svelte';
  import Clients from './Clients.svelte';
  import ManageReps from './ManageReps.svelte';
  import HotLeadsSubmit from './HotLeadsSubmit.svelte';

  let currentTab = 'dashboard';
  let currentTheme = 'light';
  let cartCount = 0;
  let contracts = [];
  let allStores = [];
  let savedProspects = [];
  let analyticsView = 'year';
  let analyticsZone = 'all';

  // Dashboard stats
  let prospectsThisWeek = 0;
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
  let showAppointmentsDetail = false;
  let thisMonthContracts = [];
  let pendingRenewalsData = [];

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

  function getNextCycle() {
    // Zone 07 cycle schedule:
    // Install dates (7th of month): A=Jan/Apr/Jul/Oct, B=Feb/May/Aug/Nov, C=Mar/Jun/Sep/Dec
    // Selling cycle switches on the 11th, one cycle ahead:
    //   After A installs (Apr 7) → C selling starts Apr 11
    //   After B installs (May 7) → A selling starts May 11  
    //   After C installs (Jun 7) → B selling starts Jun 11
    // Pattern: A install → sell C, B install → sell A, C install → sell B
    const now = new Date();
    const installCycles = [
      { name: 'A', months: [0, 3, 6, 9] },
      { name: 'B', months: [1, 4, 7, 10] },
      { name: 'C', months: [2, 5, 8, 11] },
    ];
    const sellingAfter = { 'A': 'C', 'B': 'A', 'C': 'B' };

    // Find next install date (7th of month)
    let nearestInstall = null;
    for (const cycle of installCycles) {
      for (const m of cycle.months) {
        let d = new Date(now.getFullYear(), m, 7);
        if (d <= now) d = new Date(now.getFullYear() + 1, m, 7);
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

      // Selling cycle starts on the 11th of the same month as install
      const sellDate = new Date(nearestInstall.date);
      sellDate.setDate(11);
      const sellDiff = Math.ceil((sellDate - now) / 86400000);
      nextSellingCycle = sellingAfter[nearestInstall.name];
      nextSellingDate = sellDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      nextSellingDays = sellDiff;
    }
  }

  function loadDailyGoal() {
    try {
      const today = new Date().toISOString().slice(0, 10);
      const saved = JSON.parse(localStorage.getItem('impro_daily_goal') || '{}');
      if (saved.date === today) {
        dailyGoal = saved;
      } else {
        dailyGoal = { date: today, target: saved.target || 20, calls: 0 };
      }
    } catch { dailyGoal = { date: new Date().toISOString().slice(0, 10), target: 20, calls: 0 }; }
  }

  function saveDailyGoal() {
    dailyGoal.date = new Date().toISOString().slice(0, 10);
    localStorage.setItem('impro_daily_goal', JSON.stringify(dailyGoal));
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
      
      const unique = Object.keys(byDay).sort().reverse();
      let s = 0;
      const today = new Date().toISOString().slice(0, 10);
      let checkDate = today;
      for (let i = 0; i < 365; i++) {
        if (unique.includes(checkDate)) {
          s++;
        } else if (checkDate !== today) {
          break;
        }
        const d = new Date(checkDate);
        d.setDate(d.getDate() - 1);
        checkDate = d.toISOString().slice(0, 10);
      }
      streak = s;
    } catch { streak = 0; }
  }

  function updateCartCount() {
    try { cartCount = JSON.parse(localStorage.getItem('indoormedia_cart') || '[]').length; } catch { cartCount = 0; }
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
      const searchesThisWeek = searches.filter(s => new Date(s.date) >= weekAgo).length;
      
      // Count phone clicks this week
      const phoneCalls = JSON.parse(localStorage.getItem('impro_phone_clicks') || '[]');
      const callsThisWeek = phoneCalls.filter(c => new Date(c.date) >= weekAgo).length;
      
      // Total activity = saved + searches + phone clicks
      prospectsThisWeek = savedThisWeek + searchesThisWeek + callsThisWeek;
      if (prospectsThisWeek === 0) prospectsThisWeek = saved.length; // fallback to total saved
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
      const d = new Date(c.date);
      return d.getMonth() === thisMonth && d.getFullYear() === thisYear;
    });
    const lastMonthContracts = myContracts.filter(c => {
      const d = new Date(c.date);
      return d.getMonth() === lastMonth && d.getFullYear() === lastMonthYear;
    });
    
    revenueThisMonth = thisMonthContracts.reduce((sum, c) => sum + (c.total_amount || 0), 0);
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

    // Rep's monthly revenue (individual, not team total)
    repMonthlyRevenue = thisMonthContracts.reduce((sum, c) => sum + (c.total_amount || 0), 0);

    // Leaderboard — rank by this month's revenue
    const repTotals = {};
    contracts.filter(c => {
      const d = new Date(c.date);
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

    // Pending renewals count (loaded async separately)
    fetch(import.meta.env.BASE_URL + 'data/pending_renewals.json')
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

    // Upcoming appointments from synced Google Calendar
    fetch(import.meta.env.BASE_URL + 'data/appointments.json')
      .then(r => r.json())
      .then(appts => {
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
        
        // Filter to future events
        const upcoming = myAppts.filter(a => new Date(a.start) >= now)
          .map(a => ({
            title: a.title,
            date: a.start,
            end: a.end,
            location: a.location,
            attendees: a.attendees || [],
            type: a.is_prospect_visit ? 'prospect' : 'calendar',
            store: a.store,
            phone: a.phone,
          }));
        upcomingAppointments = upcoming.slice(0, 8);
      })
      .catch(() => { upcomingAppointments = []; });

    getNextCycle();
    loadDailyGoal();
    calcStreak();
  }

  onMount(async () => {
    theme.subscribe(t => currentTheme = t);
    updateCartCount();
    const interval = setInterval(updateCartCount, 2000);

    try {
      const [contractsRes, storesRes] = await Promise.all([
        fetch(import.meta.env.BASE_URL + 'data/contracts.json'),
        fetch(import.meta.env.BASE_URL + 'data/stores.json')
      ]);
      const contractsData = await contractsRes.json();
      contracts = contractsData.contracts || [];
      allStores = await storesRes.json().catch(() => []);
      computeDashboardStats();
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    }

    return () => clearInterval(interval);
  });

  function getFilteredContracts() {
    if (analyticsZone === 'all') return contracts;
    return contracts.filter(c => (c.zone || '') === analyticsZone);
  }

  function getAvailableZones() {
    const zones = new Set();
    contracts.forEach(c => { if (c.zone) zones.add(c.zone); });
    return Array.from(zones).sort();
  }

  function getYearlyStats() {
    const filtered = getFilteredContracts();
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

  function getMonthlyStats() {
    const filtered = getFilteredContracts();
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

  function getRepStats() {
    const filtered = getFilteredContracts();
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

<div class="main" data-theme={currentTheme}>
  <!-- Header -->
  <header class="header">
    <div class="header-top">
      <div class="header-logo-wrapper">
        <div class="logo-backdrop">
          <img src="{import.meta.env.BASE_URL}logo.png?v=2" alt="IndoorMedia" class="header-logo-img" />
        </div>
        <div class="header-text">
          <h1 class="portal-title">imPro</h1>
          <p class="portal-subtitle">Sales Portal</p>
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
        <button class="header-icon-btn" on:click={forgetRoogleCredentials} title="Clear Roogle login">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/></svg>
        </button>
        <button class="header-icon-btn logout-text" on:click={handleLogout}>Logout</button>
      </div>
    </div>

    <div class="header-bottom">
      <p class="user-greeting">Welcome, <strong>{$user?.name || $user?.first_name}</strong></p>
    </div>
  </header>

  <!-- Tabs -->
  <nav class="tabs">
    <button class="tab" class:active={currentTab === 'dashboard'} on:click={() => currentTab = 'dashboard'}>
      <svg class="tab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
      <span>Home</span>
    </button>
    <button class="tab" class:active={currentTab === 'prospects'} on:click={() => currentTab = 'prospects'}>
      <svg class="tab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
      <span>Prospects</span>
    </button>
    <button class="tab" class:active={currentTab === 'stores'} on:click={() => currentTab = 'stores'}>
      <svg class="tab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
      <span>Stores</span>
    </button>
    <button class="tab" class:active={currentTab === 'clients'} on:click={() => currentTab = 'clients'}>
      <svg class="tab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
      <span>Clients</span>
    </button>
    <button class="tab" class:active={currentTab === 'tools'} on:click={() => currentTab = 'tools'}>
      <svg class="tab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>
      <span>Tools</span>
    </button>
    <button class="tab" class:active={currentTab === 'products'} on:click={() => currentTab = 'products'}>
      <svg class="tab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>
      <span>Products</span>
    </button>
    <button class="tab" class:active={currentTab === 'analytics'} on:click={() => currentTab = 'analytics'}>
      <svg class="tab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
      <span>Analytics</span>
    </button>

  </nav>

  <!-- Content -->
  <div class="content">
    {#if currentTab === 'dashboard'}
      <div class="dashboard">
        <!-- Motivational Quote -->
        {#if true}
          {@const quote = getTodaysQuote()}
          <div class="quote-card">
            <p class="quote-text">"{quote.text}"</p>
            <p class="quote-author">— {quote.author}</p>
          </div>
        {/if}

        <h2>Welcome, {$user?.name || $user?.first_name}!</h2>


        <!-- Revenue + Key Stats -->
        <button class="revenue-hero clickable" on:click={() => showRevenueDetail = !showRevenueDetail}>
          <div class="revenue-amount">${repMonthlyRevenue.toLocaleString()}</div>
          <div class="revenue-label">Revenue This Month — tap for details</div>
          {#if growthPercent !== 0}
            <div class="growth-badge" class:positive={growthPercent > 0} class:negative={growthPercent < 0}>
              {growthPercent > 0 ? '↑' : '↓'} {Math.abs(growthPercent)}% vs last month
            </div>
          {/if}
          {#if leaderboardPosition > 0}
            <div class="leaderboard-badge">🏆 #{leaderboardPosition} of {leaderboardTotal} reps this month</div>
          {/if}
        </button>

        {#if showRevenueDetail}
          <div class="drill-down">
            <h4>💰 This Month's Contracts ({thisMonthContracts.length})</h4>
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

        <div class="dashboard-grid">
          <button class="stat-card clickable" on:click={() => currentTab = 'prospects'}>
            <div class="stat-icon">🎯</div>
            <h3>Prospects</h3>
            <p class="stat-value">{prospectsThisWeek}</p>
            <p class="stat-label">This Week →</p>
          </button>
          <button class="stat-card clickable" on:click={() => currentTab = 'clients'}>
            <div class="stat-icon">🔄</div>
            <h3>Renewals</h3>
            <p class="stat-value">{pendingRenewalsCount}</p>
            <p class="stat-label">Pending →</p>
          </button>
          <button class="stat-card clickable" on:click={() => showStreakDetail = !showStreakDetail}>
            <div class="stat-icon">🔥</div>
            <h3>Streak</h3>
            <p class="stat-value">{streak}</p>
            <p class="stat-label">{streak === 1 ? 'Day' : 'Days'} Active</p>
          </button>

          <button class="stat-card clickable" on:click={() => showAppointmentsDetail = !showAppointmentsDetail}>
            <div class="stat-icon">📅</div>
            <h3>Appointments</h3>
            <p class="stat-value">{upcomingAppointments.length}</p>
            <p class="stat-label">Upcoming →</p>
          </button>

          {#if nextInstallCycle}
            <div class="stat-card cycle-card">
              <div class="stat-icon">📦</div>
              <h3>Next Cycle</h3>
              <div class="cycle-info">
                <p class="cycle-line"><strong>{nextInstallCycle} Install</strong> · {nextInstallDate}</p>
                <p class="cycle-days-label">{nextInstallDays} day{nextInstallDays !== 1 ? 's' : ''}</p>
                <p class="cycle-line"><strong>{nextSellingCycle} Selling</strong> · {nextSellingDate}</p>
                <p class="cycle-days-label">{nextSellingDays} day{nextSellingDays !== 1 ? 's' : ''}</p>
              </div>
            </div>
          {/if}
        </div>

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

        {#if showAppointmentsDetail}
          <div class="drill-down">
            <h4>📅 Upcoming Appointments</h4>
            {#if upcomingAppointments.length > 0}
              <div class="appointment-list">
                {#each upcomingAppointments as appt}
                  <div class="appointment-item">
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
                  </div>
                {/each}
              </div>
            {:else}
              <p class="no-appointments">No upcoming appointments. Book one from the Prospects tab!</p>
            {/if}
          </div>
        {/if}

        <!-- Daily Goal Tracker -->
        <div class="goal-section">
          <h3>📋 Daily Goal</h3>
          <div class="goal-card">
            <div class="goal-progress">
              <div class="goal-bar">
                <div class="goal-fill" style="width: {Math.min((dailyGoal.calls / (dailyGoal.target || 20)) * 100, 100)}%"></div>
              </div>
              <div class="goal-count">{dailyGoal.calls} / {dailyGoal.target || 20}</div>
            </div>
            <p class="goal-label">Outbound Calls / Walk-ins Today</p>
            <div class="goal-actions">
              <button class="goal-btn increment" on:click={incrementCalls}>+ Log Call / Walk-in</button>
              <button class="goal-btn reset" on:click={resetDailyGoal}>↺ Reset</button>
              <div class="goal-target-set">
                <label>Goal:</label>
                <input type="number" value={dailyGoal.target || 20} on:change={(e) => setGoalTarget(e.target.value)} min="1" max="100" />
              </div>
            </div>
            {#if dailyGoal.calls >= (dailyGoal.target || 20)}
              <p class="goal-achieved">🎉 Goal reached! Keep crushing it!</p>
            {:else if dailyGoal.calls >= (dailyGoal.target || 20) * 0.5}
              <p class="goal-halfway">💪 Halfway there! Keep pushing!</p>
            {/if}
          </div>
        </div>





        <div class="quick-actions">
          <h3>Quick Actions</h3>
          <div class="action-buttons">
            <button class="action-btn" on:click={() => currentTab = 'prospects'}>
              <span class="action-icon">🎯</span>
              <span>Find Prospects</span>
            </button>
            <button class="action-btn" on:click={() => currentTab = 'stores'}>
              <span class="action-icon">🏪</span>
              <span>Search Stores</span>
            </button>
            <button class="action-btn" on:click={() => currentTab = 'clients'}>
              <span class="action-icon">🔄</span>
              <span>Renewals</span>
            </button>
            <button class="action-btn" on:click={() => currentTab = 'cart'}>
              <span class="action-icon">🛒</span>
              <span>View Cart</span>
            </button>
          </div>
        </div>
      </div>
    {:else if currentTab === 'prospects'}
      <ProspectSearch />
    {:else if currentTab === 'stores'}
      <StoreSearch />
    {:else if currentTab === 'tools'}
      <Tools />
    {:else if currentTab === 'cart'}
      <Cart />
    {:else if currentTab === 'products'}
      <Products />
    {:else if currentTab === 'clients'}
      <Clients />
    {:else if currentTab === 'analytics'}
      <div class="analytics-container">
        <h2>📊 Sales Analytics</h2>
        
        <!-- View selector -->
        <div class="period-selector">
          <button class="period-btn" class:active={analyticsView === 'year'} on:click={() => analyticsView = 'year'}>By Year</button>
          <button class="period-btn" class:active={analyticsView === 'month'} on:click={() => analyticsView = 'month'}>By Month</button>
          <button class="period-btn" class:active={analyticsView === 'rep'} on:click={() => analyticsView = 'rep'}>By Rep</button>
        </div>

        <!-- Zone filter -->
        <div class="zone-filter">
          <span class="zone-label">Zone:</span>
          <button class="zone-btn" class:active={analyticsZone === 'all'} on:click={() => analyticsZone = 'all'}>All</button>
          {#each getAvailableZones() as zone}
            <button class="zone-btn" class:active={analyticsZone === zone} on:click={() => analyticsZone = zone}>{zone}</button>
          {/each}
        </div>

        {#if analyticsZone !== 'all'}
          <p class="zone-active-label">Filtered: Zone {analyticsZone} ({getFilteredContracts().length} contracts, ${getFilteredContracts().reduce((s,c) => s + (c.total_amount||0), 0).toLocaleString()})</p>
        {/if}

        {#if analyticsView === 'year'}
          <div class="analytics-cards">
            {#each getYearlyStats() as stat}
              <div class="analytics-card">
                <div class="analytics-year">{stat.year}</div>
                <div class="analytics-amount">${(stat.total / 1000).toFixed(0)}K</div>
                <div class="analytics-count">{stat.count} contracts</div>
                {#if stat.change !== null}
                  <div class="analytics-change" class:positive={stat.change > 0} class:negative={stat.change < 0}>
                    {stat.change > 0 ? '↑' : '↓'} {Math.abs(stat.change).toFixed(1)}%
                  </div>
                {/if}
              </div>
            {/each}
          </div>
        {:else if analyticsView === 'month'}
          <div class="month-table">
            <table>
              <thead><tr><th>Month</th><th>Revenue</th><th>Contracts</th><th>Avg Deal</th></tr></thead>
              <tbody>
                {#each getMonthlyStats() as stat}
                  <tr>
                    <td>{stat.label}</td>
                    <td>${stat.total.toLocaleString()}</td>
                    <td>{stat.count}</td>
                    <td>${(stat.total / stat.count).toLocaleString(undefined, {maximumFractionDigits: 0})}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {:else if analyticsView === 'rep'}
          <div class="rep-table">
            <table>
              <thead><tr><th>Rep</th><th>2025</th><th>2026 YTD</th><th>Total</th><th>Deals</th></tr></thead>
              <tbody>
                {#each getRepStats() as stat}
                  <tr>
                    <td>{stat.rep}</td>
                    <td>${stat.y2025.toLocaleString()}</td>
                    <td>${stat.y2026.toLocaleString()}</td>
                    <td>${stat.total.toLocaleString()}</td>
                    <td>{stat.count}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {/if}
      </div>
    {:else if currentTab === 'addlead'}
      <HotLeadsSubmit
        user={$user}
        onLeadSubmitted={() => {
          // Optional: show confirmation or navigate back to prospects
          currentTab = 'prospects';
        }}
      />
    {:else if currentTab === 'manage'}
      <ManageReps />
    {/if}
  </div>
</div>

<style>
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

  /* Header */
  .header {
    background: linear-gradient(135deg, #CC0000 0%, #990000 100%);
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
    box-shadow: 0 8px 24px rgba(204, 0, 0, 0.2);
  }

  .header-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0;
    gap: 20px;
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
    gap: 10px;
    flex-shrink: 0;
  }

  .header-icon-btn {
    background: rgba(255, 255, 255, 0.15);
    border: none;
    color: white;
    cursor: pointer;
    position: relative;
    width: 40px;
    height: 40px;
    border-radius: 10px;
    transition: all 0.2s;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0;
  }

  .header-icon-btn:hover {
    background: rgba(255, 255, 255, 0.25);
    transform: translateY(-1px);
  }

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

  /* Tabs */
  .tabs {
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border-color);
    display: flex;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    padding: 0 4px;
  }

  .tab {
    flex: 1;
    min-width: fit-content;
    padding: 14px 18px;
    background: none;
    border: none;
    border-bottom: 3px solid transparent;
    color: #666;
    font-weight: 600;
    font-size: 15px;
    cursor: pointer;
    transition: all 0.2s;
    white-space: nowrap;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
  }

  .tab-icon {
    width: 22px;
    height: 22px;
    stroke: currentColor;
  }

  .tab span {
    font-size: 11px;
    letter-spacing: 0.3px;
  }

  .tab:hover {
    color: var(--text-primary);
  }

  .tab.active {
    color: #CC0000;
    border-bottom-color: #CC0000;
  }

  /* Content */
  .content {
    flex: 1;
    overflow-y: auto;
    padding: 20px;
    max-width: 1400px;
    margin: 0 auto;
    width: 100%;
    box-sizing: border-box;
  }

  /* Dashboard */
  /* Motivational Quote */
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
  .growth-badge { display: inline-block; margin-top: 8px; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; }
  .growth-badge.positive { background: #e8f5e9; color: #2e7d32; }
  .growth-badge.negative { background: #ffe0e0; color: #c33; }
  .leaderboard-badge { margin-top: 6px; font-size: 13px; color: var(--text-secondary, #aaa); }

  /* Daily Goal */
  .goal-section { margin-bottom: 16px; }
  .goal-section h3 { margin: 0 0 8px; font-size: 16px; color: var(--text-primary); }
  .goal-card {
    background: var(--bg-secondary, #1a1a2e);
    border-radius: 12px;
    padding: 16px;
    border: 1px solid var(--border-color, #333);
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
  .appointment-list { display: flex; flex-direction: column; gap: 10px; }
  .appointment-item {
    display: flex;
    align-items: flex-start;
    gap: 14px;
    background: var(--card-bg);
    border-radius: 12px;
    padding: 14px 16px;
    border: 2px solid var(--border-color);
  }
  .appt-left { min-width: 80px; flex-shrink: 0; }
  .appt-date { font-size: 13px; font-weight: 700; color: #CC0000; white-space: nowrap; }
  .appt-time { font-size: 12px; color: var(--text-tertiary); margin-top: 2px; }
  .appt-right { flex: 1; }
  .appt-title { font-size: 15px; font-weight: 600; color: var(--text-primary); margin-bottom: 4px; }
  .appt-location { font-size: 12px; color: var(--text-secondary); margin-bottom: 2px; }
  .appt-attendees { font-size: 12px; color: var(--text-tertiary); margin-bottom: 4px; }
  .appt-badge { display: inline-block; font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 4px; }
  .appt-badge.prospect { background: rgba(204,0,0,0.1); color: #CC0000; }
  .no-appointments { font-size: 13px; color: var(--text-secondary); text-align: center; padding: 12px; }

  /* Cycle Countdown */
  .cycle-card .cycle-info { margin-top: 8px; }
  .cycle-card .cycle-line { margin: 0; font-size: 13px; color: var(--text-secondary); }
  .cycle-card .cycle-line strong { color: #CC0000; }
  .cycle-card .cycle-days-label { margin: 0 0 8px; font-size: 12px; color: var(--text-tertiary); }

  /* Clickable cards */
  .clickable { cursor: pointer; transition: transform 0.15s, box-shadow 0.15s; }
  .clickable:active { transform: scale(0.97); }
  .revenue-hero.clickable { border: none; width: 100%; text-align: center; font-family: inherit; }

  /* Drill-down panels */
  .drill-down {
    background: var(--bg-secondary, #1a1a2e);
    border: 1px solid var(--border-color, #333);
    border-radius: 10px;
    padding: 14px;
    margin-bottom: 16px;
  }
  .drill-down h4 { margin: 0 0 10px; font-size: 15px; color: var(--text-primary); }
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
  }

  .dashboard h2 {
    margin: 0 0 8px;
    color: var(--text-primary);
    font-size: 24px;
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
    gap: 1.5rem;
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
    background: var(--card-bg);
    border: 2px solid var(--border-color);
    border-radius: 16px;
    padding: 2rem 1.5rem;
    text-align: center;
    min-height: 160px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    width: 100%;
  }

  .stat-icon {
    font-size: 32px;
    margin-bottom: 8px;
  }

  .stat-card h3 {
    margin: 0 0 8px;
    font-size: 14px;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .stat-value {
    margin: 0 0 4px;
    font-size: 28px;
    font-weight: 700;
    color: #CC0000;
  }

  .stat-label {
    margin: 0;
    font-size: 12px;
    color: var(--text-tertiary);
  }

  .quick-actions {
    margin-top: 32px;
  }

  .quick-actions h3 {
    margin: 0 0 16px;
    color: var(--text-primary);
    font-size: 16px;
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
    background: var(--card-bg);
    border: 2px solid var(--border-color);
    border-radius: 12px;
    cursor: pointer;
    transition: all 0.2s;
    color: var(--text-primary);
    font-weight: 600;
    font-size: 13px;
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
      font-size: 20px;
    }

    .dashboard-grid, .action-buttons {
      grid-template-columns: 1fr;
    }
  }
  /* Analytics */
  .analytics-container { padding: 16px; max-width: 100%; margin: 0 auto; width: 100%; }
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
  .analytics-card { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 12px; padding: 16px; text-align: center; }
  .analytics-year { font-size: 18px; font-weight: 700; color: var(--text-primary); margin-bottom: 8px; }
  .analytics-amount { font-size: 28px; font-weight: 800; color: #CC0000; margin-bottom: 4px; }
  .analytics-count { font-size: 12px; color: var(--text-secondary); margin-bottom: 8px; }
  .analytics-change { font-size: 14px; font-weight: 600; padding: 4px 8px; border-radius: 8px; display: inline-block; }
  .analytics-change.positive { background: #e8f5e9; color: #2e7d32; }
  .analytics-change.negative { background: #ffebee; color: #c62828; }
  .month-table, .rep-table { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 12px; overflow: hidden; }
  .month-table table, .rep-table table { width: 100%; border-collapse: collapse; }
  .month-table th, .rep-table th { background: var(--bg-secondary); padding: 12px; text-align: left; font-weight: 700; font-size: 12px; color: var(--text-secondary); text-transform: uppercase; border-bottom: 1px solid var(--border-color); }
  .month-table td, .rep-table td { padding: 12px; border-bottom: 1px solid var(--border-color); color: var(--text-primary); }
  .month-table tr:last-child td, .rep-table tr:last-child td { border-bottom: none; }
  .month-table tr:hover, .rep-table tr:hover { background: var(--bg-secondary); }
</style>
