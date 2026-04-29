<script>
	import { onMount } from 'svelte';

	let shipmentData = [];
	let storeFilter = '';
	let statusFilter = 'all';
	let sortBy = 'days-since';
	let filteredShipments = [];
	let isLoading = false;
	let summary = {
		overdue: 0,
		approaching: 0,
		recent: 0,
		inTransit: 0
	};

	const API_BASE = '/api';

	onMount(async () => {
		await loadShippingData();
	});

	async function loadShippingData() {
		isLoading = true;
		try {
			const response = await fetch(`${API_BASE}/shipping/status`);
			if (response.ok) {
				const data = await response.json();
				shipmentData = data.shipments || [];
				summary = data.summary || {};
				filterAndSort();
			}
		} catch (error) {
			console.error('Failed to load shipping data:', error);
		} finally {
			isLoading = false;
		}
	}

	function filterAndSort() {
		let results = [...shipmentData];

		// Status filter
		if (statusFilter !== 'all') {
			results = results.filter(s => s.status === statusFilter);
		}

		// Store filter
		if (storeFilter.trim()) {
			const query = storeFilter.toLowerCase();
			results = results.filter(s => 
				s.store_number?.toLowerCase().includes(query) ||
				s.store_name?.toLowerCase().includes(query)
			);
		}

		// Sort
		results.sort((a, b) => {
			switch (sortBy) {
				case 'days-since':
					return (b.days_since_delivery || 0) - (a.days_since_delivery || 0);
				case 'store-name':
					return (a.store_name || '').localeCompare(b.store_name || '');
				case 'status':
					const statusOrder = { overdue: 0, approaching: 1, recent: 2, unknown: 3 };
					return (statusOrder[a.status] || 3) - (statusOrder[b.status] || 3);
				default:
					return 0;
			}
		});

		filteredShipments = results;
	}

	function getStatusIcon(status) {
		switch (status) {
			case 'overdue':
				return '🔴';
			case 'approaching':
				return '🟡';
			case 'recent':
				return '🟢';
			case 'in-transit':
				return '🚚';
			default:
				return '❓';
		}
	}

	function getStatusBadgeClass(status) {
		return `status-badge status-${status}`;
	}

	function getAlertLevel(shipment) {
		if (shipment.status === 'overdue') return 'critical';
		if (shipment.status === 'approaching') return 'warning';
		if (shipment.in_transit_count > 0) return 'info';
		return 'normal';
	}

	function formatDate(dateStr) {
		if (!dateStr) return 'Unknown';
		return new Date(dateStr).toLocaleDateString('en-US', {
			month: 'short',
			day: 'numeric',
			year: 'numeric'
		});
	}
</script>

<div class="shipping-status mobile-first">
	<header class="shipping-header">
		<h1>🚚 Shipping & Delivery Status</h1>
		<p class="subtitle">Track inventory runout and delivery timelines</p>
	</header>

	<!-- Summary Cards -->
	<div class="summary-cards">
		<div class="summary-card status-critical">
			<div class="summary-number">🔴 {summary.overdue || 0}</div>
			<div class="summary-label">Overdue (45+ days)</div>
		</div>
		<div class="summary-card status-warning">
			<div class="summary-number">🟡 {summary.approaching || 0}</div>
			<div class="summary-label">Approaching (30-45 days)</div>
		</div>
		<div class="summary-card status-info">
			<div class="summary-number">🚚 {summary.inTransit || 0}</div>
			<div class="summary-label">In Transit</div>
		</div>
		<div class="summary-card status-success">
			<div class="summary-number">🟢 {summary.recent || 0}</div>
			<div class="summary-label">Recent (&lt;30 days)</div>
		</div>
	</div>

	<!-- Filters & Controls -->
	<div class="controls-section">
		<div class="search-box">
			<input
				type="text"
				placeholder="Search by store name or number..."
				bind:value={storeFilter}
				on:input={filterAndSort}
				class="search-input"
			/>
		</div>

		<div class="filter-row">
			<div class="filter-group">
				<label for="status-select">Status</label>
				<select
					id="status-select"
					bind:value={statusFilter}
					on:change={filterAndSort}
					class="filter-select"
				>
					<option value="all">All Statuses</option>
					<option value="overdue">Overdue (45+)</option>
					<option value="approaching">Approaching (30-45)</option>
					<option value="recent">Recent (&lt;30)</option>
					<option value="in-transit">In Transit</option>
				</select>
			</div>

			<div class="filter-group">
				<label for="sort-select">Sort By</label>
				<select
					id="sort-select"
					bind:value={sortBy}
					on:change={filterAndSort}
					class="filter-select"
				>
					<option value="days-since">Days Since Delivery</option>
					<option value="store-name">Store Name</option>
					<option value="status">Status</option>
				</select>
			</div>
		</div>
	</div>

	<!-- Results -->
	<div class="results-header">
		<p><strong>{filteredShipments.length}</strong> stores found</p>
	</div>

	{#if isLoading}
		<div class="loading">Loading delivery status...</div>
	{/if}

	<!-- Shipment List -->
	<div class="shipments-list">
		{#each filteredShipments as shipment, idx (shipment.store_number + idx)}
			{@const alertLevel = getAlertLevel(shipment)}
			<div class="shipment-card alert-{alertLevel}">
				<div class="card-top-row">
					<div class="store-info">
						<h3 class="store-name">{shipment.store_name || 'Store ' + shipment.store_number}</h3>
						<p class="store-number">#{shipment.store_number}</p>
					</div>
					<span class={getStatusBadgeClass(shipment.status)}>
						{getStatusIcon(shipment.status)} {shipment.status || 'unknown'}
					</span>
				</div>

				<div class="status-text">
					<strong>{shipment.status_text || 'Status unknown'}</strong>
				</div>

				<div class="delivery-details">
					<div class="detail-item">
						<span class="detail-label">Last Delivery</span>
						<span class="detail-value">{formatDate(shipment.last_delivery_date)}</span>
					</div>
					<div class="detail-item">
						<span class="detail-label">Days Since</span>
						<span class="detail-value">{shipment.days_since_delivery || '?'} days</span>
					</div>
					{#if shipment.in_transit_count && shipment.in_transit_count > 0}
						<div class="detail-item in-transit">
							<span class="detail-label">In Transit</span>
							<span class="detail-value">{shipment.in_transit_count} shipment(s)</span>
						</div>
					{/if}
				</div>

				{#if shipment.delivery_address}
					<div class="address-section">
						<p class="address-label">Delivery Address</p>
						<p class="address-text">{shipment.delivery_address}</p>
					</div>
				{/if}

				{#if shipment.in_transit_tracking && shipment.in_transit_tracking.length > 0}
					<div class="tracking-section">
						<h4>Tracking Numbers</h4>
						<div class="tracking-list">
							{#each shipment.in_transit_tracking as tracking}
								<a
									href={tracking.url}
									target="_blank"
									rel="noopener"
									class="tracking-link"
								>
									📦 {tracking.tracking_number}
									<span class="tracking-date">{formatDate(tracking.ship_date)}</span>
								</a>
							{/each}
						</div>
					</div>
				{/if}

				{#if shipment.tracking_url}
					<div class="action-buttons">
						<a href={shipment.tracking_url} target="_blank" rel="noopener" class="btn-track">
							Track UPS →
						</a>
					</div>
				{/if}
			</div>
		{/each}
	</div>

	{#if !isLoading && filteredShipments.length === 0}
		<div class="no-results">
			<p>No shipments found matching your filters.</p>
		</div>
	{/if}
</div>

<style>
	.shipping-status {
		padding: 1rem;
		padding-bottom: calc(120px + env(safe-area-inset-bottom, 0px));
		background: #f9f9f9;
		min-height: 100vh;
	}

	.shipping-header {
		margin-bottom: 2rem;
		text-align: center;
	}

	.shipping-header h1 {
		margin: 0;
		font-size: 1.75rem;
		color: #2c3e50;
	}

	.subtitle {
		margin: 0.5rem 0 0 0;
		color: #7f8c8d;
		font-size: 0.95rem;
	}

	/* Summary Cards */
	.summary-cards {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: 0.75rem;
		margin-bottom: 2rem;
	}

	@media (min-width: 640px) {
		.summary-cards {
			grid-template-columns: repeat(4, 1fr);
			gap: 1rem;
		}
	}

	.summary-card {
		padding: 1rem;
		border-radius: 8px;
		color: white;
		text-align: center;
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
	}

	.summary-card.status-critical {
		background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
	}

	.summary-card.status-warning {
		background: linear-gradient(135deg, #f39c12 0%, #e67e22 100%);
	}

	.summary-card.status-info {
		background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
	}

	.summary-card.status-success {
		background: linear-gradient(135deg, #27ae60 0%, #229954 100%);
	}

	.summary-number {
		font-size: 1.75rem;
		font-weight: 700;
		margin-bottom: 0.5rem;
	}

	.summary-label {
		font-size: 0.8rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.5px;
	}

	/* Controls */
	.controls-section {
		background: white;
		padding: 1.25rem;
		border-radius: 8px;
		margin-bottom: 2rem;
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
	}

	.search-box {
		margin-bottom: 1rem;
	}

	.search-input {
		width: 100%;
		padding: 0.75rem;
		font-size: 1rem;
		border: 2px solid #e0e0e0;
		border-radius: 6px;
		transition: border-color 0.2s;
	}

	.search-input:focus {
		outline: none;
		border-color: #3498db;
	}

	.filter-row {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 1rem;
	}

	.filter-group {
		display: flex;
		flex-direction: column;
	}

	.filter-group label {
		font-weight: 600;
		color: #2c3e50;
		font-size: 0.9rem;
		margin-bottom: 0.5rem;
	}

	.filter-select {
		padding: 0.75rem;
		border: 1px solid #e0e0e0;
		border-radius: 6px;
		font-size: 0.95rem;
	}

	.filter-select:focus {
		outline: none;
		border-color: #3498db;
	}

	.results-header {
		padding: 0 0.5rem;
		margin-bottom: 1rem;
		color: #7f8c8d;
		font-size: 0.95rem;
	}

	.loading {
		text-align: center;
		padding: 2rem;
		color: #7f8c8d;
	}

	/* Shipment Cards */
	.shipments-list {
		display: grid;
		grid-template-columns: 1fr;
		gap: 1rem;
		margin-bottom: 2rem;
	}

	@media (min-width: 640px) {
		.shipments-list {
			grid-template-columns: repeat(2, 1fr);
		}
	}

	.shipment-card {
		background: white;
		border-radius: 8px;
		padding: 1.25rem;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
		border-left: 4px solid #e0e0e0;
		transition: transform 0.2s, box-shadow 0.2s;
	}

	.shipment-card.alert-critical {
		border-left-color: #e74c3c;
		background: #fef5f5;
	}

	.shipment-card.alert-warning {
		border-left-color: #f39c12;
		background: #fef9f5;
	}

	.shipment-card.alert-info {
		border-left-color: #3498db;
		background: #f5f9fe;
	}

	.shipment-card.alert-normal {
		border-left-color: #27ae60;
	}

	.shipment-card:active {
		transform: translateY(-2px);
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
	}

	.card-top-row {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: 1rem;
		margin-bottom: 1rem;
	}

	.store-info {
		flex: 1;
	}

	.store-name {
		margin: 0;
		font-size: 1.15rem;
		color: #2c3e50;
	}

	.store-number {
		margin: 0.25rem 0 0 0;
		color: #7f8c8d;
		font-size: 0.9rem;
	}

	.status-badge {
		display: inline-block;
		padding: 0.5rem 0.75rem;
		border-radius: 6px;
		font-weight: 600;
		font-size: 0.85rem;
		white-space: nowrap;
		text-transform: uppercase;
	}

	.status-badge.status-overdue {
		background: #e74c3c;
		color: white;
	}

	.status-badge.status-approaching {
		background: #f39c12;
		color: white;
	}

	.status-badge.status-recent {
		background: #27ae60;
		color: white;
	}

	.status-badge.status-in-transit {
		background: #3498db;
		color: white;
	}

	.status-badge.status-unknown {
		background: #95a5a6;
		color: white;
	}

	.status-text {
		margin-bottom: 1rem;
		padding-bottom: 1rem;
		border-bottom: 1px solid #ecf0f1;
		font-size: 0.95rem;
	}

	.status-text strong {
		color: #2c3e50;
	}

	.delivery-details {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 1rem;
		margin-bottom: 1rem;
		padding: 0.75rem;
		background: #f9f9f9;
		border-radius: 6px;
	}

	.detail-item {
		display: flex;
		flex-direction: column;
	}

	.detail-item.in-transit {
		grid-column: 1 / -1;
	}

	.detail-label {
		font-size: 0.75rem;
		color: #7f8c8d;
		font-weight: 600;
		text-transform: uppercase;
	}

	.detail-value {
		font-size: 1rem;
		font-weight: 700;
		color: #2c3e50;
		margin-top: 0.25rem;
	}

	.address-section {
		margin: 1rem 0;
		padding: 0.75rem;
		background: #ecf0f1;
		border-radius: 6px;
	}

	.address-label {
		margin: 0 0 0.5rem 0;
		font-size: 0.8rem;
		color: #7f8c8d;
		font-weight: 600;
		text-transform: uppercase;
	}

	.address-text {
		margin: 0;
		font-size: 0.9rem;
		color: #2c3e50;
		line-height: 1.5;
	}

	.tracking-section {
		margin-top: 1rem;
		padding-top: 1rem;
		border-top: 1px solid #ecf0f1;
	}

	.tracking-section h4 {
		margin: 0 0 0.75rem 0;
		font-size: 0.9rem;
		color: #2c3e50;
	}

	.tracking-list {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.tracking-link {
		display: block;
		padding: 0.75rem;
		background: #e8f4f8;
		border-radius: 6px;
		text-decoration: none;
		color: #3498db;
		font-weight: 600;
		font-size: 0.9rem;
		transition: background 0.2s;
	}

	.tracking-link:active {
		background: #d0e8f0;
	}

	.tracking-date {
		display: block;
		font-size: 0.75rem;
		color: #7f8c8d;
		font-weight: 400;
		margin-top: 0.25rem;
	}

	.action-buttons {
		display: grid;
		grid-template-columns: 1fr;
		gap: 0.5rem;
		margin-top: 1rem;
		padding-top: 1rem;
		border-top: 1px solid #ecf0f1;
	}

	.btn-track {
		display: block;
		padding: 0.75rem 1rem;
		background: #3498db;
		color: white;
		text-decoration: none;
		border-radius: 6px;
		text-align: center;
		font-weight: 600;
		font-size: 0.9rem;
		transition: background 0.2s;
	}

	.btn-track:active {
		background: #2980b9;
	}

	.no-results {
		text-align: center;
		padding: 2rem;
		background: white;
		border-radius: 8px;
		color: #7f8c8d;
	}
</style>
