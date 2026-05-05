<script>
  import { onMount, onDestroy } from 'svelte';
  import { user } from '../lib/stores.js';

  export let appointments = [];
  export let dailyGoal = { calls: 0, target: 20 };
  export let savedProspects = 0;
  export let revenueThisMonth = 0;
  export let onClose = () => {};
  export let onLogCall = () => {};

  let speaking = false;
  let wakeLock = null;
  let currentTime = new Date();
  let timeInterval;

  $: firstName = ($user?.name || $user?.first_name || 'Rep').split(' ')[0];
  $: nextAppt = appointments.length > 0 ? appointments[0] : null;
  $: goalPercent = Math.min((dailyGoal.calls / (dailyGoal.target || 20)) * 100, 100);

  onMount(async () => {
    // Keep screen on
    try {
      if ('wakeLock' in navigator) {
        wakeLock = await navigator.wakeLock.request('screen');
      }
    } catch (e) { console.warn('Wake lock not available:', e); }

    // Update clock
    timeInterval = setInterval(() => { currentTime = new Date(); }, 60000);

    // Auto-briefing on launch
    speakBriefing();
  });

  onDestroy(() => {
    if (wakeLock) wakeLock.release();
    if (timeInterval) clearInterval(timeInterval);
    window.speechSynthesis.cancel();
  });

  function speakBriefing() {
    if (!('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    speaking = true;

    const hour = new Date().getHours();
    const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';

    let text = `${greeting}, ${firstName}. Here's your briefing. `;

    // Appointments
    if (appointments.length === 0) {
      text += `You have no upcoming appointments. `;
    } else if (appointments.length === 1) {
      const a = appointments[0];
      const time = new Date(a.date).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
      text += `You have 1 appointment coming up. ${a.title || 'Appointment'} at ${time}. `;
      if (a.location) text += `Located at ${a.location}. `;
    } else {
      const a = appointments[0];
      const time = new Date(a.date).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
      text += `You have ${appointments.length} appointments. Next up: ${a.title || 'Appointment'} at ${time}. `;
    }

    // Daily goal
    text += `Daily goal: ${dailyGoal.calls} of ${dailyGoal.target || 20} calls logged. `;
    if (dailyGoal.calls >= (dailyGoal.target || 20)) {
      text += `You've hit your goal! Keep it up. `;
    } else {
      text += `${(dailyGoal.target || 20) - dailyGoal.calls} to go. `;
    }

    // Revenue
    if (revenueThisMonth > 0) {
      text += `Revenue this month: $${revenueThisMonth.toLocaleString()}. `;
    }

    text += `Have a great run out there.`;

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.95;
    utterance.pitch = 1;
    utterance.onend = () => { speaking = false; };
    utterance.onerror = () => { speaking = false; };
    window.speechSynthesis.speak(utterance);
  }

  function stopSpeaking() {
    window.speechSynthesis.cancel();
    speaking = false;
  }

  function navigateToAppt() {
    if (!nextAppt?.location) return;
    const url = `https://maps.apple.com/?daddr=${encodeURIComponent(nextAppt.location)}`;
    window.open(url, '_blank');
  }

  function callProspect() {
    if (!nextAppt) return;
    // Try to extract phone from appointment details
    const details = nextAppt.details || nextAppt.description || '';
    const phoneMatch = details.match(/Phone:\s*([\d\-\(\)\s\+]+)/i);
    if (phoneMatch) {
      window.open(`tel:${phoneMatch[1].trim()}`, '_self');
    }
  }
</script>

<div class="driving-overlay">
  <div class="driving-header">
    <div class="driving-time">{currentTime.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}</div>
    <button class="driving-close" on:click={onClose}>✕ Exit</button>
  </div>

  <!-- Next Appointment — BIG and tappable -->
  <div class="driving-section">
    {#if nextAppt}
      <div class="driving-appt">
        <div class="driving-appt-label">NEXT UP</div>
        <div class="driving-appt-title">{nextAppt.title || 'Appointment'}</div>
        <div class="driving-appt-time">
          {new Date(nextAppt.date).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}
          {#if nextAppt.location}
            <span class="driving-appt-loc">📍 {nextAppt.location}</span>
          {/if}
        </div>
        <div class="driving-appt-actions">
          {#if nextAppt.location}
            <button class="driving-btn driving-btn-nav" on:click={navigateToAppt}>
              🗺️ Navigate
            </button>
          {/if}
          <button class="driving-btn driving-btn-call" on:click={callProspect}>
            📞 Call
          </button>
        </div>
      </div>
    {:else}
      <div class="driving-appt">
        <div class="driving-appt-label">NO APPOINTMENTS</div>
        <div class="driving-appt-title" style="font-size: 24px;">You're free to prospect! 🎯</div>
      </div>
    {/if}
  </div>

  <!-- Stats Row — big, glanceable -->
  <div class="driving-stats">
    <div class="driving-stat">
      <div class="driving-stat-value">{dailyGoal.calls}/{dailyGoal.target || 20}</div>
      <div class="driving-stat-label">Calls</div>
      <div class="driving-goal-bar">
        <div class="driving-goal-fill" style="width: {goalPercent}%"></div>
      </div>
    </div>
    <div class="driving-stat">
      <div class="driving-stat-value">{appointments.length}</div>
      <div class="driving-stat-label">Appts</div>
    </div>
    <div class="driving-stat">
      <div class="driving-stat-value">${(revenueThisMonth / 1000).toFixed(1)}K</div>
      <div class="driving-stat-label">Month</div>
    </div>
  </div>

  <!-- Big Action Buttons -->
  <div class="driving-actions">
    <button class="driving-big-btn driving-big-log" on:click={onLogCall}>
      📞 Log Call
    </button>
    <button class="driving-big-btn driving-big-brief" on:click={speaking ? stopSpeaking : speakBriefing}>
      {speaking ? '⏹️ Stop' : '🔊 Briefing'}
    </button>
  </div>
</div>

<style>
  .driving-overlay {
    position: fixed; top: 0; left: 0; right: 0; bottom: 0; z-index: 9999;
    background: #0a0a0a; color: #fff;
    display: flex; flex-direction: column; padding: 16px;
    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro', sans-serif;
    overflow-y: auto;
  }

  .driving-header {
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 20px; flex-shrink: 0;
  }
  .driving-time { font-size: 18px; font-weight: 300; color: #aaa; }
  .driving-close {
    font-size: 16px; padding: 8px 16px; border-radius: 20px;
    border: 1px solid #444; background: none; color: #aaa; cursor: pointer;
  }

  .driving-section { flex: 1; display: flex; align-items: center; justify-content: center; }

  .driving-appt { text-align: center; width: 100%; }
  .driving-appt-label { font-size: 12px; font-weight: 700; letter-spacing: 2px; color: #CC0000; margin-bottom: 8px; }
  .driving-appt-title { font-size: 28px; font-weight: 700; margin-bottom: 8px; line-height: 1.2; }
  .driving-appt-time { font-size: 18px; color: #aaa; margin-bottom: 16px; }
  .driving-appt-loc { display: block; font-size: 14px; margin-top: 4px; color: #888; }

  .driving-appt-actions { display: flex; gap: 12px; justify-content: center; }
  .driving-btn {
    padding: 14px 28px; border-radius: 14px; font-size: 18px; font-weight: 600;
    border: none; cursor: pointer; min-width: 140px;
  }
  .driving-btn-nav { background: #1a73e8; color: white; }
  .driving-btn-call { background: #34a853; color: white; }
  .driving-btn:active { opacity: 0.8; transform: scale(0.97); }

  .driving-stats {
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;
    margin: 20px 0; flex-shrink: 0;
  }
  .driving-stat {
    background: #1a1a1a; border-radius: 14px; padding: 14px; text-align: center;
  }
  .driving-stat-value { font-size: 26px; font-weight: 700; }
  .driving-stat-label { font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: 1px; margin-top: 2px; }
  .driving-goal-bar { height: 4px; background: #333; border-radius: 2px; margin-top: 8px; overflow: hidden; }
  .driving-goal-fill { height: 100%; background: #CC0000; border-radius: 2px; transition: width 0.3s; }

  .driving-actions {
    display: grid; grid-template-columns: 1fr 1fr; gap: 12px;
    flex-shrink: 0; padding-bottom: env(safe-area-inset-bottom, 16px);
  }
  .driving-big-btn {
    padding: 20px; border-radius: 16px; font-size: 20px; font-weight: 700;
    border: none; cursor: pointer; text-align: center;
  }
  .driving-big-btn:active { opacity: 0.8; transform: scale(0.97); }
  .driving-big-log { background: #CC0000; color: white; }
  .driving-big-brief { background: #2a2a2a; color: white; border: 1px solid #444; }
</style>
