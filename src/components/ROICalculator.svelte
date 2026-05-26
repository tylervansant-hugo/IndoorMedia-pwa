<script>
  import { padAmount } from '../lib/stores.js';
  
  let investment = 3500;
  let avgSpend = 50;
  let newCustomers = 25;
  let cogsPercent = 35;
  
  // Compounding factor: 12 * 13 / 2 = 78
  $: grossRevenue = newCustomers * avgSpend * 78;
  $: cogs = grossRevenue * (cogsPercent / 100);
  $: netRevenue = grossRevenue - cogs;
  $: netProfit = netRevenue - investment;
  $: roi = investment > 0 ? ((netProfit / investment) * 100).toFixed(0) : 0;
</script>

<div class="roi-container">
  <h2>📊 ROI Calculator</h2>
  <p class="subtitle">Show customers their return on investment</p>
  
  <div class="inputs">
    <div class="input-group">
      <label>Investment ($)</label>
      <input type="range" min="500" max="15000" step="100" bind:value={investment}>
      <span class="value">${investment.toLocaleString()}</span>
    </div>
    
    <div class="input-group">
      <label>Avg Customer Spend ($)</label>
      <input type="range" min="10" max="200" step="5" bind:value={avgSpend}>
      <span class="value">${avgSpend}</span>
    </div>
    
    <div class="input-group">
      <label>New Customers / Month</label>
      <input type="range" min="1" max="100" step="1" bind:value={newCustomers}>
      <span class="value">{newCustomers}</span>
    </div>
    
    <div class="input-group">
      <label>COGS %</label>
      <input type="range" min="0" max="70" step="5" bind:value={cogsPercent}>
      <span class="value">{cogsPercent}%</span>
    </div>
  </div>
  
  <div class="results">
    <div class="result-card">
      <div class="result-label">Gross Annual Revenue</div>
      <div class="result-value">${grossRevenue.toLocaleString()}</div>
    </div>
    
    <div class="result-card cost">
      <div class="result-label">COGS ({cogsPercent}%)</div>
      <div class="result-value">-${cogs.toLocaleString()}</div>
    </div>
    
    <div class="result-card">
      <div class="result-label">Net Annual Revenue</div>
      <div class="result-value">${netRevenue.toLocaleString()}</div>
    </div>
    
    <div class="result-card net" class:positive={netProfit > 0} class:negative={netProfit <= 0}>
      <div class="result-label">Net Profit</div>
      <div class="result-value">${netProfit.toLocaleString()}</div>
    </div>
    
    <div class="result-card roi-card" class:great={roi > 200} class:good={roi > 100 && roi <= 200} class:low={roi <= 100}>
      <div class="result-label">ROI</div>
      <div class="result-value big">{roi}%</div>
    </div>
    
    <div class="result-card">
      <div class="result-label">New Customers (Year)</div>
      <div class="result-value">{newCustomers * 12}</div>
    </div>
  </div>
  
  <p class="formula-note">Formula: {newCustomers} customers × ${avgSpend} spend × 78 (compounding monthly). Each month adds {newCustomers} new customers who keep returning.</p>
</div>

<style>
  .roi-container { max-width: 600px; margin: 0 auto; }
  h2 { margin: 0; font-size: 20px; color: #1a1a1a; }
  .subtitle { color: #666; font-size: 14px; margin: 4px 0 20px 0; }
  
  .inputs {
    background: white;
    border-radius: 10px;
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  }
  
  .input-group {
    margin-bottom: 16px;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
  }
  
  .input-group:last-child { margin-bottom: 0; }
  
  .input-group label {
    width: 100%;
    font-size: 13px;
    font-weight: 600;
    color: #333;
  }
  
  .input-group input[type="range"] {
    flex: 1;
    accent-color: #CC0000;
    height: 6px;
  }
  
  .input-group .value {
    min-width: 60px;
    text-align: right;
    font-weight: 700;
    font-size: 16px;
    color: #1a1a1a;
  }
  
  .results {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }
  
  .result-card {
    background: white;
    border-radius: 10px;
    padding: 16px;
    text-align: center;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  }
  
  .result-label { font-size: 12px; color: #666; margin-bottom: 4px; }
  .result-value { font-size: 20px; font-weight: 800; color: #1a1a1a; }
  .result-value.big { font-size: 36px; }
  
  .result-card.positive { border-left: 4px solid #2e7d32; }
  .result-card.negative { border-left: 4px solid #c62828; }
  .result-card.net .result-value { color: #2e7d32; }
  .result-card.negative .result-value { color: #c62828; }
  
  .roi-card.great { background: #e8f5e9; }
  .roi-card.great .result-value { color: #2e7d32; }
  .roi-card.good { background: #fff3e0; }
  .roi-card.good .result-value { color: #e65100; }
  .roi-card.low { background: #fce4ec; }
  .roi-card.low .result-value { color: #c62828; }
  
  .formula-note {
    margin-top: 16px;
    font-size: 12px;
    color: #888;
    text-align: center;
    font-style: italic;
  }
  
  @media (max-width: 480px) {
    .results { grid-template-columns: 1fr; }
  }
</style>
