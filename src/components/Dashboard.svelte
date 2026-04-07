<script>
  import { onMount } from 'svelte';
  
  export let user;
  
  let prospects = [];
  let stats = { total: 0, interested: 0, followup: 0, closed: 0, avgScore: 0 };
  
  onMount(async () => {
    try {
      const res = await fetch(import.meta.env.BASE_URL + 'data/prospect_data.json');
      const data = await res.json();
      const reps = data.reps || {};
      
      // Get all prospects across all reps
      let allProspects = [];
      for (const [repId, rep] of Object.entries(reps)) {
        const saved = rep.saved_prospects || {};
        for (const [pid, p] of Object.entries(saved)) {
          allProspects.push({ ...p, repName: rep.name, repId });
        }
      }
      
      prospects = allProspects;
      
      // Calculate stats
      stats.total = prospects.length;
      stats.interested = prospects.filter(p => p.status === 'interested').length;
      stats.followup = prospects.filter(p => p.status === 'follow-up').length;
      stats.closed = prospects.filter(p => p.status === 'closed').length;
      
      const scores = prospects.filter(p => p.score).map(p => p.score);
      stats.avgScore = scores.length ? (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(1) : 0;
      
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    }
  });
  
  // Rep leaderboard
  $: repStats = (() => {
    const map = {};
    prospects.forEach(p => {
      if (!map[p.repName]) map[p.repName] = { name: p.repName, total: 0, closed: 0 };
      map[p.repName].total++;
      if (p.status === 'closed') map[p.repName].closed++;
    });
    return Object.values(map).sort((a, b) => b.closed - a.closed);
  })();
</script>

<div class="dashboard">
  <h2>📊 Performance Dashboard</h2>
  
  <div class="stat-grid">
    <div class="stat-card">
      <div class="stat-number">{stats.total}</div>
      <div class="stat-label">Total Prospects</div>
    </div>
    <div class="stat-card interested">
      <div class="stat-number">{stats.interested}</div>
      <div class="stat-label">Interested</div>
    </div>
    <div class="stat-card followup">
      <div class="stat-number">{stats.followup}</div>
      <div class="stat-label">Follow-up</div>
    </div>
    <div class="stat-card closed">
      <div class="stat-number">{stats.closed}</div>
      <div class="stat-label">Closed</div>
    </div>
  </div>
  
  <div class="stat-card wide">
    <div class="stat-number">{stats.avgScore}%</div>
    <div class="stat-label">Average Prospect Score</div>
  </div>
  
  {#if repStats.length > 0}
    <h3>👥 Rep Leaderboard</h3>
    <div class="leaderboard">
      {#each repStats as rep, i}
        <div class="leader-row">
          <span class="rank">#{i + 1}</span>
          <span class="leader-name">{rep.name}</span>
          <span class="leader-stats">{rep.closed} closed / {rep.total} total</span>
        </div>
      {/each}
    </div>
  {/if}
  
  <h3>🔄 Pipeline</h3>
  <div class="pipeline">
    <div class="pipe-stage">
      <div class="pipe-bar" style="width: {stats.total ? (stats.interested / stats.total * 100) : 0}%; background: #1565c0;"></div>
      <span>Interested ({stats.interested})</span>
    </div>
    <div class="pipe-stage">
      <div class="pipe-bar" style="width: {stats.total ? (stats.followup / stats.total * 100) : 0}%; background: #e65100;"></div>
      <span>Follow-up ({stats.followup})</span>
    </div>
    <div class="pipe-stage">
      <div class="pipe-bar" style="width: {stats.total ? (stats.closed / stats.total * 100) : 0}%; background: #2e7d32;"></div>
      <span>Closed ({stats.closed})</span>
    </div>
  </div>
</div>

<style>
  .dashboard { max-width: 800px; margin: 0 auto; }
  h2 { margin: 0 0 20px 0; font-size: 20px; color: #1a1a1a; }
  h3 { margin: 24px 0 12px 0; font-size: 16px; color: #333; }
  
  .stat-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
    margin-bottom: 12px;
  }
  
  .stat-card {
    background: white;
    border-radius: 10px;
    padding: 20px;
    text-align: center;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    border-left: 4px solid #ddd;
  }
  
  .stat-card.interested { border-left-color: #1565c0; }
  .stat-card.followup { border-left-color: #e65100; }
  .stat-card.closed { border-left-color: #2e7d32; }
  .stat-card.wide { margin-bottom: 12px; border-left-color: #CC0000; }
  
  .stat-number { font-size: 32px; font-weight: 800; color: #1a1a1a; }
  .stat-label { font-size: 13px; color: #666; margin-top: 4px; }
  
  .leaderboard {
    background: white;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  }
  
  .leader-row {
    display: flex;
    align-items: center;
    padding: 12px 16px;
    border-bottom: 1px solid #f0f0f0;
    gap: 12px;
  }
  
  .leader-row:last-child { border-bottom: none; }
  
  .rank {
    font-weight: 700;
    color: #CC0000;
    min-width: 30px;
  }
  
  .leader-name { flex: 1; font-weight: 600; color: #333; }
  .leader-stats { font-size: 13px; color: #666; }
  
  .pipeline {
    background: white;
    border-radius: 10px;
    padding: 16px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  }
  
  .pipe-stage {
    margin-bottom: 12px;
  }
  
  .pipe-stage:last-child { margin-bottom: 0; }
  
  .pipe-bar {
    height: 24px;
    border-radius: 4px;
    min-width: 4px;
    margin-bottom: 4px;
    transition: width 0.5s;
  }
  
  .pipe-stage span { font-size: 12px; color: #666; }
  
  @media (max-width: 480px) {
    .stat-grid { grid-template-columns: repeat(2, 1fr); gap: 8px; }
    .stat-number { font-size: 24px; }
    .stat-card { padding: 14px; }
  }
</style>
