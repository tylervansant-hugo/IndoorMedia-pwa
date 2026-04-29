<script>
	import { onMount } from 'svelte';

	let repsData = [];
	let selectedTimeframe = 'monthly'; // 'monthly' or 'yearly'
	let loading = true;
	let error = null;

	onMount(async () => {
		try {
			const response = await fetch('/api/dashboard/metrics');
			if (!response.ok) throw new Error('Failed to load metrics');
			const data = await response.json();
			repsData = data.reps || [];
			loading = false;
		} catch (err) {
			error = err.message;
			loading = false;
		}
	});

	// Calculate aggregates
	$: totalSearches = repsData.reduce((sum, rep) => sum + (rep.searches || 0), 0);
	$: totalProspects = repsData.reduce((sum, rep) => sum + (rep.saved_prospects || 0), 0);
	$: totalDeals = repsData.reduce((sum, rep) => sum + (rep.closed_deals || 0), 0);

	// Sort by performance metric
	$: leaderboard = [...repsData].sort((a, b) => {
		const aScore = selectedTimeframe === 'monthly' ? (a.monthly_score || 0) : (a.yearly_score || 0);
		const bScore = selectedTimeframe === 'monthly' ? (b.monthly_score || 0) : (b.yearly_score || 0);
		return bScore - aScore;
	});

	function formatDate(dateString) {
		return new Date(dateString).toLocaleDateString('en-US', {
			month: 'short',
			day: 'numeric',
			year: 'numeric'
		});
	}

	function getMetricIcon(metric) {
		const icons = {
			searches: '🔍',
			prospects: '👥',
			deals: '💰'
		};
		return icons[metric] || '📊';
	}
</script>

<div class="dashboard">
	<div class="header">
		<h1>📊 Performance Dashboard</h1>
		<div class="timeframe-toggle">
			<button
				class:active={selectedTimeframe === 'monthly'}
				on:click={() => (selectedTimeframe = 'monthly')}
			>
				Monthly
			</button>
			<button
				class:active={selectedTimeframe === 'yearly'}
				on:click={() => (selectedTimeframe = 'yearly')}
			>
				Yearly
			</button>
		</div>
	</div>

	{#if loading}
		<div class="loading">Loading metrics...</div>
	{:else if error}
		<div class="error">Error: {error}</div>
	{:else}
		<!-- Key Metrics Cards -->
		<div class="metrics-grid">
			<div class="metric-card">
				<div class="metric-icon">🔍</div>
				<div class="metric-content">
					<div class="metric-label">Total Searches</div>
					<div class="metric-value">{totalSearches}</div>
					<div class="metric-subtitle">
						{selectedTimeframe === 'monthly' ? 'This Month' : 'This Year'}
					</div>
				</div>
			</div>

			<div class="metric-card">
				<div class="metric-icon">👥</div>
				<div class="metric-content">
					<div class="metric-label">Saved Prospects</div>
					<div class="metric-value">{totalProspects}</div>
					<div class="metric-subtitle">Active Pipeline</div>
				</div>
			</div>

			<div class="metric-card">
				<div class="metric-icon">💰</div>
				<div class="metric-content">
					<div class="metric-label">Closed Deals</div>
					<div class="metric-value">{totalDeals}</div>
					<div class="metric-subtitle">
						{selectedTimeframe === 'monthly' ? 'This Month' : 'This Year'}
					</div>
				</div>
			</div>

			<div class="metric-card">
				<div class="metric-icon">🏆</div>
				<div class="metric-content">
					<div class="metric-label">Team Size</div>
					<div class="metric-value">{repsData.length}</div>
					<div class="metric-subtitle">Active Reps</div>
				</div>
			</div>
		</div>

		<!-- Sales Pipeline Status -->
		<div class="section">
			<h2>📈 Sales Pipeline Status</h2>
			<div class="pipeline">
				<div class="pipeline-stage">
					<div class="stage-name">Interested</div>
					<div class="stage-count">
						{repsData.reduce((sum, rep) => sum + (rep.interested || 0), 0)}
					</div>
					<div class="stage-bar">
						<div
							class="stage-fill"
							style="width: {Math.min(
								100,
								(repsData.reduce((sum, rep) => sum + (rep.interested || 0), 0) / Math.max(totalProspects, 1)) * 100
							)}%"
						/>
					</div>
				</div>

				<div class="pipeline-stage">
					<div class="stage-name">Follow-up</div>
					<div class="stage-count">
						{repsData.reduce((sum, rep) => sum + (rep.followup || 0), 0)}
					</div>
					<div class="stage-bar">
						<div
							class="stage-fill"
							style="width: {Math.min(
								100,
								(repsData.reduce((sum, rep) => sum + (rep.followup || 0), 0) / Math.max(totalProspects, 1)) * 100
							)}%"
						/>
					</div>
				</div>

				<div class="pipeline-stage">
					<div class="stage-name">Proposal</div>
					<div class="stage-count">
						{repsData.reduce((sum, rep) => sum + (rep.proposal || 0), 0)}
					</div>
					<div class="stage-bar">
						<div
							class="stage-fill"
							style="width: {Math.min(
								100,
								(repsData.reduce((sum, rep) => sum + (rep.proposal || 0), 0) / Math.max(totalProspects, 1)) * 100
							)}%"
						/>
					</div>
				</div>

				<div class="pipeline-stage">
					<div class="stage-name">Closed</div>
					<div class="stage-count">
						{repsData.reduce((sum, rep) => sum + (rep.closed || 0), 0)}
					</div>
					<div class="stage-bar">
						<div
							class="stage-fill closed"
							style="width: {Math.min(
								100,
								(repsData.reduce((sum, rep) => sum + (rep.closed || 0), 0) / Math.max(totalProspects, 1)) * 100
							)}%"
						/>
					</div>
				</div>
			</div>
		</div>

		<!-- Team Leaderboard -->
		<div class="section">
			<h2>🏆 Team Leaderboard</h2>
			<div class="leaderboard">
				{#each leaderboard as rep, index (rep.id)}
					<div class="leaderboard-row">
						<div class="rank">#{index + 1}</div>
						<div class="rep-info">
							<div class="rep-name">{rep.name}</div>
							<div class="rep-role">{rep.base_location || 'Field'}</div>
						</div>
						<div class="rep-metrics">
							<span class="metric-chip">{rep.searches || 0} 🔍</span>
							<span class="metric-chip">{rep.saved_prospects || 0} 👥</span>
							<span class="metric-chip">{rep.closed_deals || 0} 💰</span>
						</div>
						<div class="rep-score">
							{#if selectedTimeframe === 'monthly'}
								<div class="score-label">Monthly</div>
								<div class="score-value">{(rep.monthly_score || 0).toFixed(0)}</div>
							{:else}
								<div class="score-label">Yearly</div>
								<div class="score-value">{(rep.yearly_score || 0).toFixed(0)}</div>
							{/if}
						</div>
					</div>
				{/each}
			</div>
		</div>

		<!-- Comparison Chart (Monthly vs Yearly) -->
		<div class="section">
			<h2>📊 Performance Trends</h2>
			<div class="comparison-info">
				<p>Track individual performance across timeframes</p>
			</div>
		</div>
	{/if}
</div>

<style>
	.dashboard {
		padding: 1rem;
		padding-bottom: calc(120px + env(safe-area-inset-bottom, 0px));
		background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
		min-height: 100vh;
	}

	.header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1.5rem;
		gap: 1rem;
		flex-wrap: wrap;
	}

	.header h1 {
		margin: 0;
		font-size: 1.5rem;
		color: #2c3e50;
	}

	.timeframe-toggle {
		display: flex;
		gap: 0.5rem;
		background: white;
		border-radius: 0.5rem;
		padding: 0.25rem;
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
	}

	.timeframe-toggle button {
		padding: 0.5rem 1rem;
		border: none;
		background: transparent;
		cursor: pointer;
		border-radius: 0.4rem;
		transition: all 0.3s ease;
		font-weight: 600;
		color: #666;
	}

	.timeframe-toggle button.active {
		background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
		color: white;
	}

	.loading,
	.error {
		text-align: center;
		padding: 2rem;
		background: white;
		border-radius: 0.75rem;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
	}

	.error {
		color: #e74c3c;
		background: #fadbd8;
	}

	.metrics-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
		gap: 1rem;
		margin-bottom: 2rem;
	}

	.metric-card {
		display: flex;
		align-items: center;
		gap: 1rem;
		background: white;
		padding: 1.25rem;
		border-radius: 0.75rem;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
		transition: transform 0.3s ease, box-shadow 0.3s ease;
	}

	.metric-card:hover {
		transform: translateY(-4px);
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
	}

	.metric-icon {
		font-size: 2.5rem;
		line-height: 1;
	}

	.metric-content {
		flex: 1;
	}

	.metric-label {
		font-size: 0.875rem;
		color: #666;
		text-transform: uppercase;
		letter-spacing: 0.5px;
	}

	.metric-value {
		font-size: 2rem;
		font-weight: 700;
		color: #2c3e50;
		line-height: 1;
	}

	.metric-subtitle {
		font-size: 0.75rem;
		color: #999;
		margin-top: 0.25rem;
	}

	.section {
		background: white;
		padding: 1.5rem;
		border-radius: 0.75rem;
		margin-bottom: 1.5rem;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
	}

	.section h2 {
		margin: 0 0 1.5rem 0;
		font-size: 1.25rem;
		color: #2c3e50;
	}

	.pipeline {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.pipeline-stage {
		display: flex;
		align-items: center;
		gap: 1rem;
	}

	.stage-name {
		min-width: 100px;
		font-weight: 600;
		color: #2c3e50;
	}

	.stage-count {
		min-width: 40px;
		text-align: right;
		font-weight: 700;
		color: #667eea;
	}

	.stage-bar {
		flex: 1;
		height: 8px;
		background: #ecf0f1;
		border-radius: 4px;
		overflow: hidden;
	}

	.stage-fill {
		height: 100%;
		background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
		border-radius: 4px;
		transition: width 0.5s ease;
	}

	.stage-fill.closed {
		background: linear-gradient(90deg, #11998e 0%, #38ef7d 100%);
	}

	.leaderboard {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.leaderboard-row {
		display: flex;
		align-items: center;
		gap: 1rem;
		padding: 1rem;
		background: linear-gradient(135deg, #f9fafb 0%, #f3f4f6 100%);
		border-radius: 0.5rem;
		border-left: 4px solid #667eea;
		transition: all 0.3s ease;
	}

	.leaderboard-row:hover {
		background: linear-gradient(135deg, #f0f4ff 0%, #e8ecff 100%);
		border-left-color: #764ba2;
	}

	.rank {
		min-width: 40px;
		font-size: 1.5rem;
		font-weight: 700;
		color: #667eea;
		text-align: center;
	}

	.rep-info {
		flex: 1;
	}

	.rep-name {
		font-weight: 700;
		color: #2c3e50;
		margin-bottom: 0.25rem;
	}

	.rep-role {
		font-size: 0.875rem;
		color: #999;
	}

	.rep-metrics {
		display: flex;
		gap: 0.5rem;
		flex-wrap: wrap;
	}

	.metric-chip {
		display: inline-block;
		padding: 0.25rem 0.75rem;
		background: white;
		border-radius: 1rem;
		font-size: 0.75rem;
		font-weight: 600;
		color: #2c3e50;
		border: 1px solid #e0e0e0;
		transition: all 0.3s ease;
	}

	.metric-chip:hover {
		border-color: #667eea;
		color: #667eea;
	}

	.rep-score {
		text-align: right;
		min-width: 70px;
	}

	.score-label {
		font-size: 0.75rem;
		color: #999;
		text-transform: uppercase;
	}

	.score-value {
		font-size: 1.5rem;
		font-weight: 700;
		color: #667eea;
	}

	.comparison-info {
		padding: 1rem;
		background: #f0f4ff;
		border-left: 4px solid #667eea;
		border-radius: 0.5rem;
		color: #2c3e50;
	}

	@media (max-width: 640px) {
		.dashboard {
			padding: 0.75rem;
		}

		.header {
			flex-direction: column;
			align-items: flex-start;
		}

		.metrics-grid {
			grid-template-columns: 1fr;
		}

		.leaderboard-row {
			flex-wrap: wrap;
		}

		.rep-metrics {
			order: 3;
			width: 100%;
		}

		.rep-score {
			min-width: auto;
		}
	}
</style>
