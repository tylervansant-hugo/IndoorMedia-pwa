<script>
  let storePrice = 3500;
  let avgTicket = 50;
  let couponValue = 10;
  let redemptionsPerMonth = 30;
  let cogsPercent = 35;
  
  $: netPerRedemption = (avgTicket - couponValue) * (1 - cogsPercent / 100);
  $: monthlyRevenue = redemptionsPerMonth * (avgTicket - couponValue);
  $: monthlyProfit = redemptionsPerMonth * netPerRedemption;
  $: monthlyAdCost = (storePrice + 125) / 12;
  $: monthlyNet = monthlyProfit - monthlyAdCost;
  $: roi = monthlyAdCost > 0 ? ((monthlyProfit / monthlyAdCost) * 100).toFixed(0) : 0;
  $: breakEven = netPerRedemption > 0 ? Math.ceil(monthlyAdCost / netPerRedemption) : 0;
  $: annualNet = monthlyNet * 12;
</script>

<div class="roi-container">
  <h2>📊 ROI Calculator</h2>
  <p class="subtitle">Show customers their return on investment</p>
  
  <div class="inputs">
    <div class="input-group">
      <label>Annual Store Price ($)</label>
      <input type="range" min="1000" max="10000" step="100" bind:value={storePrice}>
      <span class="value">${storePrice.toLocaleString()}</span>
    </div>
    
    <div class="input-group">
      <label>Avg Ticket Size ($)</label>
      <input type="range" min="10" max="200" step="5" bind:value={avgTicket}>
      <span class="value">${avgTicket}</span>
    </div>
    
    <div class="input-group">
      <label>Coupon Value ($)</label>
      <input type="range" min="1" max="50" step="1" bind:value={couponValue}>
      <span class="value">${couponValue}</span>
    </div>
    
    <div class="input-group">
      <label>Redemptions / Month</label>
      <input type="range" min="5" max="200" step="5" bind:value={redemptionsPerMonth}>
      <span class="value">{redemptionsPerMonth}</span>
    </div>
    
    <div class="input-group">
      <label>COGS %</label>
      <input type="range" min="10" max="70" step="5" bind:value={cogsPercent}>
      <span class="value">{cogsPercent}%</span>
    </div>
  </div>
  
  <div class="results">
    <div class="result-card profit">
      <div class="result-label">Monthly Profit</div>
      <div class="result-value">${monthlyProfit.toFixed(2)}</div>
    </div>
    
    <div class="result-card cost">
      <div class="result-label">Monthly Ad Cost</div>
      <div class="result-value">${monthlyAdCost.toFixed(2)}</div>
    </div>
    
    <div class="result-card net" class:positive={monthlyNet > 0} class:negative={monthlyNet <= 0}>
      <div class="result-label">Monthly Net</div>
      <div class="result-value">${monthlyNet.toFixed(2)}</div>
    </div>
    
    <div class="result-card roi-card" class:great={roi > 200} class:good={roi > 100 && roi <= 200} class:low={roi <= 100}>
      <div class="result-label">ROI</div>
      <div class="result-value big">{roi}%</div>
    </div>
    
    <div class="result-card">
      <div class="result-label">Break-Even Redemptions</div>
      <div class="result-value">{breakEven}/month</div>
    </div>
    
    <div class="result-card">
      <div class="result-label">Annual Net Profit</div>
      <div class="result-value">${annualNet.toFixed(2)}</div>
    </div>
  </div>
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
  
  @media (max-width: 480px) {
    .results { grid-template-columns: 1fr; }
  }
</style>
