<script>
	import { onMount } from 'svelte';

	let reps = [];
	let selectedRep = null;
	let repStats = {};
	let storeAllocations = [];
	let performanceMetrics = {};
	let isLoading = false;
	let activeTab = 'overview';

	const API_BASE = '/api';

	onMount(async () => {
		await loadAdminData();
	});

	async function loadAdminData() {
		isLoading = true;
		try {
			const [repsRes, statsRes, allocRes] = await Promise.all([
				fetch(`${API_BASE}/admin/reps`),
				fetch(`${API_BASE}/admin/stats`),
				fetch(`${API_BASE}/admin/allocations`)
			]);

			if (repsRes.ok) reps = await repsRes.json();
			if (statsRes.ok) repStats = await statsRes.json();
			if (allocRes.ok) storeAllocations = await allocRes.json();

			// Calculate performance metrics
			calculatePerformanceMetrics();
		} catch (error) {
			console.error('Failed to load admin data:', error);
		} finally {
			isLoading = false;
		}
	}

	function calculatePerformanceMetrics() {
		reps.forEach(rep => {
			const stats = repStats[rep.id] || {};
			performanceMetrics[rep.id] = {
				totalProspects: stats.saved_prospects ? Object.keys(stats.saved_prospects).length : 0,
				totalSearches: stats.session_searches || 0,
				conversionRate: stats.saved_prospects ? ((Object.keys(stats.saved_prospects).length / (stats.session_searches || 1)) * 100).toFixed(1) : 0,
				baseLocation: rep.base_location || 'Unknown'
			};
		});
	}

	function selectRep(rep) {
		selectedRep = rep;
	}

	function getRepStatus(rep) {
		if (!rep.role) return 'inactive';
		return rep.role === 'manager' ? 'manager' : 'active';
	}

	function formatDate(dateStr) {
		if (!dateStr) return 'N/A';
		return new Date(dateStr).toLocaleDateString();
	}
</script>

<div class="admin-panel mobile-first">
	<header class="admin-header">
		<h1>⚙️ Admin Dashboard</h1>
		<p class="subtitle">Manage reps, territories, and performance</p>
	</header>

	<!-- Tabs -->
	<div class="admin-tabs">
		<button
			class="tab-btn {activeTab === 'overview' ? 'active' : ''}"
			on:click={() => (activeTab = 'overview')}
		>
			Overview
		</button>
		<button
			class="tab-btn {activeTab === 'reps' ? 'active' : ''}"
			on:click={() => (activeTab = 'reps')}
		>
			Reps & Teams
		</button>
		<button
			class="tab-btn {activeTab === 'allocations' ? 'active' : ''}"
			on:click={() => (activeTab = 'allocations')}
		>
			Allocations
		</button>
		<button
			class="tab-btn {activeTab === 'settings' ? 'active' : ''}"
			on:click={() => (activeTab = 'settings')}
		>
			Settings
		</button>
	</div>

	{#if isLoading}
		<div class="loading">Loading admin data...</div>
	{/if}

	<!-- Overview Tab -->
	{#if activeTab === 'overview' && !isLoading}
		<section class="tab-content">
			<h2>Dashboard Overview</h2>

			<div class="metrics-grid">
				<div class="metric-card">
					<div class="metric-icon">👥</div>
					<div class="metric-info">
						<p class="metric-label">Total Reps</p>
						<p class="metric-value">{reps.length}</p>
					</div>
				</div>

				<div class="metric-card">
					<div class="metric-icon">🎯</div>
					<div class="metric-info">
						<p class="metric-label">Prospects Saved</p>
						<p class="metric-value">
							{reps.reduce((sum, rep) => {
								return sum + (repStats[rep.id]?.saved_prospects ? Object.keys(repStats[rep.id].saved_prospects).length : 0);
							}, 0)}
						</p>
					</div>
				</div>

				<div class="metric-card">
					<div class="metric-icon">🔍</div>
					<div class="metric-info">
						<p class="metric-label">Total Searches</p>
						<p class="metric-value">
							{reps.reduce((sum, rep) => sum + (repStats[rep.id]?.session_searches || 0), 0)}
						</p>
					</div>
				</div>

				<div class="metric-card">
					<div class="metric-icon">📍</div>
					<div class="metric-info">
						<p class="metric-label">Territories</p>
						<p class="metric-value">
							{new Set(reps.map(r => r.base_location).filter(Boolean)).size}
						</p>
					</div>
				</div>
			</div>
		</section>
	{/if}

	<!-- Reps & Teams Tab -->
	{#if activeTab === 'reps' && !isLoading}
		<section class="tab-content">
			<h2>Representatives & Teams</h2>

			{#if selectedRep}
				<div class="rep-detail-view">
					<button on:click={() => (selectedRep = null)} class="btn-back">← Back to List</button>

					<div class="rep-detail-header">
						<h3>{selectedRep.display_name || selectedRep.contract_name}</h3>
						<span class="role-badge role-{getRepStatus(selectedRep)}">{selectedRep.role || 'rep'}</span>
					</div>

					<div class="rep-detail-info">
						<div class="info-row">
							<span class="label">Email:</span>
							<span class="value">{selectedRep.email || 'N/A'}</span>
						</div>
						<div class="info-row">
							<span class="label">Base Location:</span>
							<span class="value">{selectedRep.base_location || 'Unknown'}</span>
						</div>
						<div class="info-row">
							<span class="label">Registered:</span>
							<span class="value">{formatDate(selectedRep.registered_at)}</span>
						</div>
					</div>

					<div class="rep-metrics">
						<h4>Performance</h4>
						<div class="metric-mini">
							<span>Prospects Saved:</span>
							<strong>{performanceMetrics[selectedRep.id]?.totalProspects || 0}</strong>
						</div>
						<div class="metric-mini">
							<span>Searches Completed:</span>
							<strong>{performanceMetrics[selectedRep.id]?.totalSearches || 0}</strong>
						</div>
						<div class="metric-mini">
							<span>Conversion Rate:</span>
							<strong>{performanceMetrics[selectedRep.id]?.conversionRate || 0}%</strong>
						</div>
					</div>
				</div>
			{:else}
				<div class="reps-list">
					{#each reps as rep (rep.id || rep.contract_name)}
						<div class="rep-card" on:click={() => selectRep(rep)}>
							<div class="rep-card-header">
								<h4>{rep.display_name || rep.contract_name}</h4>
								<span class="role-badge role-{getRepStatus(rep)}">{rep.role || 'rep'}</span>
							</div>

							{#if rep.base_location}
								<p class="rep-location">📍 {rep.base_location}</p>
							{/if}

							<div class="rep-card-stats">
								<div class="stat">
									<span class="stat-value">{performanceMetrics[rep.id]?.totalProspects || 0}</span>
									<span class="stat-label">Prospects</span>
								</div>
								<div class="stat">
									<span class="stat-value">{performanceMetrics[rep.id]?.totalSearches || 0}</span>
									<span class="stat-label">Searches</span>
								</div>
								<div class="stat">
									<span class="stat-value">{performanceMetrics[rep.id]?.conversionRate || 0}%</span>
									<span class="stat-label">Conversion</span>
								</div>
							</div>

							<small class="rep-date">Since {formatDate(rep.registered_at)}</small>
						</div>
					{/each}
				</div>
			{/if}
		</section>
	{/if}

	<!-- Allocations Tab -->
	{#if activeTab === 'allocations' && !isLoading}
		<section class="tab-content">
			<h2>Store Allocations & Coverage</h2>

			<div class="allocations-view">
				{#each reps as rep (rep.id)}
					{@const allocation = storeAllocations.find(a => a.rep_id === rep.id)}
					{@const prospects = repStats[rep.id]?.saved_prospects || {}}

					<div class="allocation-card">
						<h4>{rep.display_name || rep.contract_name}</h4>
						<p class="allocation-location">📍 {rep.base_location || 'TBD'}</p>

						<div class="allocation-metrics">
							<div class="alloc-metric">
								<span class="label">Assigned Stores:</span>
								<span class="value">{allocation?.store_count || 0}</span>
							</div>
							<div class="alloc-metric">
								<span class="label">Prospects:</span>
								<span class="value">{Object.keys(prospects).length}</span>
							</div>
							<div class="alloc-metric">
								<span class="label">Coverage:</span>
								<span class="value">{allocation?.coverage_percent || 0}%</span>
							</div>
						</div>

						{#if Object.keys(prospects).length > 0}
							<div class="prospect-list">
								<h5>Top Prospects</h5>
								<ul>
									{#each Object.values(prospects).slice(0, 3) as prospect}
										<li>{prospect.name} - {prospect.status}</li>
									{/each}
								</ul>
							</div>
						{/if}
					</div>
				{/each}
			</div>
		</section>
	{/if}

	<!-- Settings Tab -->
	{#if activeTab === 'settings' && !isLoading}
		<section class="tab-content">
			<h2>System Settings</h2>

			<div class="settings-form">
				<div class="setting-group">
					<label for="sync-freq">Data Sync Frequency</label>
					<select id="sync-freq" class="setting-input">
						<option>Every 5 minutes</option>
						<option>Every 15 minutes</option>
						<option>Every hour</option>
						<option>Manual only</option>
					</select>
				</div>

				<div class="setting-group">
					<label for="alert-threshold">Low Stock Alert Threshold</label>
					<input type="number" id="alert-threshold" value="10" class="setting-input" />
				</div>

				<div class="setting-group">
					<label for="overdue-days">Overdue Delivery Days</label>
					<input type="number" id="overdue-days" value="45" class="setting-input" />
				</div>

				<button class="btn-save">💾 Save Settings</button>
			</div>
		</section>
	{/if}
</div>

<style>
	.admin-panel {
		padding: 1rem;
		padding-bottom: calc(120px + env(safe-area-inset-bottom, 0px));
		background: #f5f5f5;
		min-height: 100vh;
	}

	.admin-header {
		margin-bottom: 1.5rem;
		text-align: center;
	}

	.admin-header h1 {
		margin: 0;
		font-size: 1.75rem;
		color: #2c3e50;
	}

	.subtitle {
		margin: 0.5rem 0 0 0;
		color: #7f8c8d;
		font-size: 0.95rem;
	}

	.admin-tabs {
		display: flex;
		gap: 0.5rem;
		margin-bottom: 2rem;
		background: white;
		padding: 0.5rem;
		border-radius: 8px;
		overflow-x: auto;
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
	}

	.tab-btn {
		flex: 1;
		min-width: 80px;
		padding: 0.75rem 1rem;
		border: none;
		background: transparent;
		color: #7f8c8d;
		font-weight: 600;
		cursor: pointer;
		border-radius: 6px;
		transition: all 0.2s;
		font-size: 0.85rem;
		white-space: nowrap;
	}

	.tab-btn.active {
		background: #3498db;
		color: white;
	}

	.tab-content {
		animation: fadeIn 0.2s;
	}

	@keyframes fadeIn {
		from {
			opacity: 0;
		}
		to {
			opacity: 1;
		}
	}

	.tab-content h2 {
		margin-top: 0;
		color: #2c3e50;
		font-size: 1.35rem;
	}

	.loading {
		text-align: center;
		padding: 2rem;
		color: #7f8c8d;
	}

	/* Metrics Grid */
	.metrics-grid {
		display: grid;
		grid-template-columns: 1fr;
		gap: 1rem;
		margin-bottom: 2rem;
	}

	@media (min-width: 640px) {
		.metrics-grid {
			grid-template-columns: repeat(2, 1fr);
		}
	}

	@media (min-width: 1024px) {
		.metrics-grid {
			grid-template-columns: repeat(4, 1fr);
		}
	}

	.metric-card {
		background: white;
		padding: 1.5rem;
		border-radius: 8px;
		display: flex;
		align-items: center;
		gap: 1rem;
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
	}

	.metric-icon {
		font-size: 2rem;
		flex-shrink: 0;
	}

	.metric-label {
		margin: 0;
		font-size: 0.85rem;
		color: #7f8c8d;
		text-transform: uppercase;
		font-weight: 600;
	}

	.metric-value {
		margin: 0.25rem 0 0 0;
		font-size: 1.75rem;
		font-weight: 700;
		color: #2c3e50;
	}

	/* Reps List */
	.reps-list {
		display: grid;
		grid-template-columns: 1fr;
		gap: 1rem;
	}

	@media (min-width: 640px) {
		.reps-list {
			grid-template-columns: repeat(2, 1fr);
		}
	}

	.rep-card {
		background: white;
		padding: 1.25rem;
		border-radius: 8px;
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
		cursor: pointer;
		transition: transform 0.2s, box-shadow 0.2s;
	}

	.rep-card:active {
		transform: translateY(-2px);
		box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
	}

	.rep-card-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 1rem;
		margin-bottom: 0.75rem;
	}

	.rep-card-header h4 {
		margin: 0;
		color: #2c3e50;
		font-size: 1.1rem;
	}

	.role-badge {
		display: inline-block;
		padding: 0.35rem 0.75rem;
		border-radius: 20px;
		font-size: 0.75rem;
		font-weight: 600;
		text-transform: uppercase;
	}

	.role-badge.role-manager {
		background: #f39c12;
		color: white;
	}

	.role-badge.role-active {
		background: #27ae60;
		color: white;
	}

	.role-badge.role-inactive {
		background: #95a5a6;
		color: white;
	}

	.rep-location {
		margin: 0.5rem 0;
		color: #7f8c8d;
		font-size: 0.9rem;
	}

	.rep-card-stats {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 0.75rem;
		padding: 0.75rem;
		background: #f9f9f9;
		border-radius: 6px;
		margin: 0.75rem 0;
	}

	.stat {
		display: flex;
		flex-direction: column;
		align-items: center;
		text-align: center;
	}

	.stat-value {
		font-size: 1.3rem;
		font-weight: 700;
		color: #3498db;
	}

	.stat-label {
		font-size: 0.7rem;
		color: #7f8c8d;
		text-transform: uppercase;
		margin-top: 0.25rem;
	}

	.rep-date {
		color: #95a5a6;
		font-size: 0.8rem;
	}

	/* Rep Detail View */
	.rep-detail-view {
		background: white;
		padding: 1.25rem;
		border-radius: 8px;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
	}

	.btn-back {
		background: none;
		border: none;
		color: #3498db;
		font-weight: 600;
		cursor: pointer;
		margin-bottom: 1rem;
		font-size: 0.95rem;
	}

	.rep-detail-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1.5rem;
		padding-bottom: 1rem;
		border-bottom: 2px solid #ecf0f1;
	}

	.rep-detail-header h3 {
		margin: 0;
		color: #2c3e50;
	}

	.rep-detail-info {
		margin-bottom: 1.5rem;
	}

	.info-row {
		display: flex;
		justify-content: space-between;
		padding: 0.75rem 0;
		border-bottom: 1px solid #ecf0f1;
	}

	.info-row .label {
		font-weight: 600;
		color: #7f8c8d;
		font-size: 0.9rem;
	}

	.info-row .value {
		color: #2c3e50;
		text-align: right;
		word-break: break-word;
	}

	.rep-metrics {
		background: #f9f9f9;
		padding: 1rem;
		border-radius: 6px;
	}

	.rep-metrics h4 {
		margin-top: 0;
		color: #2c3e50;
		font-size: 0.95rem;
	}

	.metric-mini {
		display: flex;
		justify-content: space-between;
		padding: 0.5rem 0;
		font-size: 0.9rem;
		color: #555;
	}

	.metric-mini strong {
		color: #2c3e50;
		font-weight: 700;
	}

	/* Allocations */
	.allocations-view {
		display: grid;
		grid-template-columns: 1fr;
		gap: 1rem;
	}

	@media (min-width: 640px) {
		.allocations-view {
			grid-template-columns: repeat(2, 1fr);
		}
	}

	.allocation-card {
		background: white;
		padding: 1.25rem;
		border-radius: 8px;
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
	}

	.allocation-card h4 {
		margin-top: 0;
		color: #2c3e50;
	}

	.allocation-location {
		margin: 0.5rem 0;
		color: #7f8c8d;
		font-size: 0.9rem;
	}

	.allocation-metrics {
		background: #f9f9f9;
		padding: 0.75rem;
		border-radius: 6px;
		margin: 1rem 0;
	}

	.alloc-metric {
		display: flex;
		justify-content: space-between;
		padding: 0.5rem 0;
		font-size: 0.9rem;
	}

	.alloc-metric .label {
		color: #7f8c8d;
	}

	.alloc-metric .value {
		font-weight: 700;
		color: #3498db;
	}

	.prospect-list {
		margin-top: 1rem;
		padding-top: 1rem;
		border-top: 1px solid #ecf0f1;
	}

	.prospect-list h5 {
		margin: 0 0 0.75rem 0;
		font-size: 0.9rem;
		color: #2c3e50;
	}

	.prospect-list ul {
		margin: 0;
		padding-left: 1.25rem;
		list-style: none;
	}

	.prospect-list li {
		padding: 0.35rem 0;
		font-size: 0.85rem;
		color: #555;
	}

	.prospect-list li::before {
		content: '→ ';
		color: #3498db;
		font-weight: 600;
	}

	/* Settings */
	.settings-form {
		background: white;
		padding: 1.5rem;
		border-radius: 8px;
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
	}

	.setting-group {
		margin-bottom: 1.5rem;
		display: flex;
		flex-direction: column;
	}

	.setting-group label {
		margin-bottom: 0.5rem;
		font-weight: 600;
		color: #2c3e50;
		font-size: 0.95rem;
	}

	.setting-input {
		padding: 0.75rem;
		border: 1px solid #e0e0e0;
		border-radius: 6px;
		font-size: 0.95rem;
	}

	.setting-input:focus {
		outline: none;
		border-color: #3498db;
	}

	.btn-save {
		padding: 1rem;
		background: #27ae60;
		color: white;
		border: none;
		border-radius: 6px;
		font-weight: 600;
		cursor: pointer;
		font-size: 1rem;
		width: 100%;
	}

	.btn-save:active {
		opacity: 0.9;
	}
</style>
