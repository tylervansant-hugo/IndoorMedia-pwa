<script>
	import { onMount } from 'svelte';

	let stores = [];
	let selectedStore = null;
	let inventoryData = {
		store_num: '',
		starting_cases: 20,
		units_per_roll: 4,
		rolls_per_case: 12,
		current_rolls: 0,
		delivery_date: '',
		cycle: '5-day'
	};
	let auditStep = 'store-select'; // 'store-select', 'inventory-entry', 'audit-result'
	let auditResult = null;
	let loading = true;
	let error = null;
	let sendingEmail = false;

	onMount(async () => {
		try {
			const response = await fetch('/api/audit/stores');
			if (!response.ok) throw new Error('Failed to load stores');
			const data = await response.json();
			stores = data.stores || [];
			loading = false;
		} catch (err) {
			error = err.message;
			loading = false;
		}
	});

	function selectStore(store) {
		selectedStore = store;
		inventoryData.store_num = store.number;
		auditStep = 'inventory-entry';
		error = null;
	}

	function resetAudit() {
		selectedStore = null;
		auditStep = 'store-select';
		auditResult = null;
		inventoryData = {
			store_num: '',
			starting_cases: 20,
			units_per_roll: 4,
			rolls_per_case: 12,
			current_rolls: 0,
			delivery_date: '',
			cycle: '5-day'
		};
	}

	async function submitInventory() {
		if (!inventoryData.store_num || !inventoryData.delivery_date || !inventoryData.current_rolls) {
			error = 'Please fill in all required fields';
			return;
		}

		try {
			const response = await fetch('/api/audit/calculate', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(inventoryData)
			});

			if (!response.ok) throw new Error('Failed to calculate audit');

			const result = await response.json();
			auditResult = result;
			auditStep = 'audit-result';
			error = null;
		} catch (err) {
			error = err.message;
		}
	}

	async function sendAuditEmail() {
		if (!auditResult) return;

		sendingEmail = true;
		try {
			const response = await fetch('/api/audit/email', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					store_num: inventoryData.store_num,
					audit_result: auditResult
				})
			});

			if (response.ok) {
				auditResult.email_sent = true;
			}
		} catch (err) {
			error = 'Failed to send email: ' + err.message;
		} finally {
			sendingEmail = false;
		}
	}

	function getStatusColor(status) {
		const colors = {
			SUFFICIENT: '#27ae60',
			WARNING: '#f39c12',
			INSUFFICIENT: '#e74c3c'
		};
		return colors[status] || '#95a5a6';
	}

	function getStatusIcon(status) {
		const icons = {
			SUFFICIENT: '✅',
			WARNING: '⚠️',
			INSUFFICIENT: '🚨'
		};
		return icons[status] || '❓';
	}
</script>

<div class="audit-container">
	<div class="header">
		<h1>🏪 Audit Store</h1>
		<p class="subtitle">Track tape inventory and calculate days until runout</p>
	</div>

	{#if loading}
		<div class="loading">Loading stores...</div>
	{:else if error}
		<div class="error">⚠️ {error}</div>
	{:else}
		<!-- Step 1: Store Selection -->
		{#if auditStep === 'store-select'}
			<div class="section">
				<h2>Select Store</h2>
				<div class="stores-grid">
					{#if stores.length === 0}
						<div class="empty-state">
							<p>No stores available</p>
						</div>
					{:else}
						{#each stores as store (store.number)}
							<button
								class="store-card"
								on:click={() => selectStore(store)}
							>
								<div class="store-icon">🏬</div>
								<div class="store-name">{store.name || store.number}</div>
								<div class="store-number">#{store.number}</div>
								{#if store.location}
									<div class="store-location">📍 {store.location}</div>
								{/if}
							</button>
						{/each}
					{/if}
				</div>
			</div>

		<!-- Step 2: Inventory Entry -->
		{:else if auditStep === 'inventory-entry'}
			<div class="section">
				<div class="step-header">
					<button class="back-btn" on:click={resetAudit}>← Back</button>
					<h2>Store #{inventoryData.store_num}</h2>
				</div>

				<form on:submit|preventDefault={submitInventory} class="audit-form">
					<div class="form-group">
						<label for="delivery_date">
							📅 Next Delivery Date <span class="required">*</span>
						</label>
						<input
							type="date"
							id="delivery_date"
							bind:value={inventoryData.delivery_date}
							required
						/>
					</div>

					<div class="form-group">
						<label for="starting_cases">
							📦 Starting Cases on Shelf
						</label>
						<div class="input-group">
							<input
								type="number"
								id="starting_cases"
								bind:value={inventoryData.starting_cases}
								min="0"
							/>
							<span class="unit">cases</span>
						</div>
						<div class="help-text">Typical: 20 cases per store</div>
					</div>

					<div class="form-group">
						<label for="current_rolls">
							📜 Current Rolls on Hand <span class="required">*</span>
						</label>
						<div class="input-group">
							<input
								type="number"
								id="current_rolls"
								bind:value={inventoryData.current_rolls}
								min="0"
								required
							/>
							<span class="unit">rolls</span>
						</div>
						<div class="help-text">Total rolls currently in inventory</div>
					</div>

					<div class="form-group">
						<label for="units_per_roll">
							🎯 Units per Roll
						</label>
						<div class="input-group">
							<input
								type="number"
								id="units_per_roll"
								bind:value={inventoryData.units_per_roll}
								min="1"
							/>
							<span class="unit">units</span>
						</div>
					</div>

					<div class="form-group">
						<label for="cycle">
							⏱️ Sales Cycle
						</label>
						<select id="cycle" bind:value={inventoryData.cycle}>
							<option value="3-day">3-day cycle</option>
							<option value="5-day">5-day cycle</option>
							<option value="7-day">7-day cycle</option>
							<option value="custom">Custom</option>
						</select>
					</div>

					<button type="submit" class="btn-primary">
						Calculate Runout
					</button>
				</form>
			</div>

		<!-- Step 3: Audit Result -->
		{:else if auditStep === 'audit-result' && auditResult}
			<div class="section">
				<div class="result-header">
					<button class="back-btn" on:click={resetAudit}>← New Audit</button>
					<h2>Audit Report</h2>
				</div>

				<!-- Status Alert -->
				<div
					class="status-alert"
					style="border-left-color: {getStatusColor(auditResult.status)}"
				>
					<div class="alert-icon">{getStatusIcon(auditResult.status)}</div>
					<div class="alert-content">
						<div class="alert-title">{auditResult.status}</div>
						<div class="alert-message">{auditResult.message}</div>
					</div>
				</div>

				<!-- Key Metrics -->
				<div class="metrics-grid">
					<div class="metric">
						<div class="metric-label">Days Until Runout</div>
						<div class="metric-value" style="color: {getStatusColor(auditResult.status)}">
							{auditResult.days_until_runout.toFixed(1)}
						</div>
						<div class="metric-unit">days</div>
					</div>

					<div class="metric">
						<div class="metric-label">Days Until Delivery</div>
						<div class="metric-value">{auditResult.days_until_delivery}</div>
						<div class="metric-unit">days</div>
					</div>

					<div class="metric">
						<div class="metric-label">Current Inventory</div>
						<div class="metric-value">{auditResult.total_rolls}</div>
						<div class="metric-unit">rolls</div>
					</div>

					<div class="metric">
						<div class="metric-label">Daily Usage</div>
						<div class="metric-value">{auditResult.daily_usage.toFixed(1)}</div>
						<div class="metric-unit">rolls/day</div>
					</div>
				</div>

				<!-- Detailed Info -->
				<div class="info-section">
					<h3>📊 Calculation Details</h3>
					<div class="info-grid">
						<div class="info-row">
							<span class="label">Starting Cases:</span>
							<span class="value">{inventoryData.starting_cases} cases</span>
						</div>
						<div class="info-row">
							<span class="label">Current Rolls:</span>
							<span class="value">{inventoryData.current_rolls} rolls</span>
						</div>
						<div class="info-row">
							<span class="label">Total Units:</span>
							<span class="value">{auditResult.total_units} units</span>
						</div>
						<div class="info-row">
							<span class="label">Delivery Date:</span>
							<span class="value">{new Date(inventoryData.delivery_date).toLocaleDateString()}</span>
						</div>
						<div class="info-row">
							<span class="label">Days Until Runout:</span>
							<span class="value" style="color: {getStatusColor(auditResult.status); font-weight: 700;">
								{auditResult.days_until_runout.toFixed(1)} days
							</span>
						</div>
					</div>
				</div>

				<!-- Recommendation -->
				{#if auditResult.status === 'INSUFFICIENT'}
					<div class="recommendation critical">
						<div class="rec-icon">🚨</div>
						<div class="rec-content">
							<div class="rec-title">CRITICAL: Low Inventory</div>
							<div class="rec-text">
								Inventory will run out BEFORE the next delivery. Immediate action required.
								{#if auditResult.email_sent}
									<div class="email-status">✓ Email sent to Tyler</div>
								{:else}
									<button class="btn-email" on:click={sendAuditEmail} disabled={sendingEmail}>
										{sendingEmail ? 'Sending...' : '📧 Send Critical Alert'}
									</button>
								{/if}
							</div>
						</div>
					</div>
				{:else if auditResult.status === 'WARNING'}
					<div class="recommendation warning">
						<div class="rec-icon">⚠️</div>
						<div class="rec-content">
							<div class="rec-title">Warning: Tight Inventory</div>
							<div class="rec-text">
								Inventory is cutting it close. Consider prioritizing delivery or reducing usage if possible.
							</div>
						</div>
					</div>
				{:else}
					<div class="recommendation success">
						<div class="rec-icon">✅</div>
						<div class="rec-content">
							<div class="rec-title">Sufficient Inventory</div>
							<div class="rec-text">
								You have enough stock to cover the delivery cycle.
							</div>
						</div>
					</div>
				{/if}

				<!-- Action Buttons -->
				<div class="action-buttons">
					{#if auditResult.status === 'INSUFFICIENT' && !auditResult.email_sent}
						<button
							class="btn-critical"
							on:click={sendAuditEmail}
							disabled={sendingEmail}
						>
							{sendingEmail ? '📧 Sending...' : '📧 Alert Tyler (Critical)'}
						</button>
					{/if}
					<button class="btn-secondary" on:click={resetAudit}>
						📊 New Audit
					</button>
				</div>
			</div>
		{/if}
	{/if}
</div>

<style>
	.audit-container {
		padding: 1rem;
		background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
		min-height: 100vh;
	}

	.header {
		margin-bottom: 2rem;
		text-align: center;
	}

	.header h1 {
		margin: 0 0 0.5rem 0;
		font-size: 1.75rem;
		color: #2c3e50;
	}

	.subtitle {
		margin: 0;
		color: #666;
		font-size: 1rem;
	}

	.loading,
	.error {
		text-align: center;
		padding: 2rem;
		background: white;
		border-radius: 0.75rem;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
		margin: 1rem 0;
	}

	.error {
		color: #e74c3c;
		background: #fadbd8;
		border-left: 4px solid #e74c3c;
	}

	.section {
		background: white;
		padding: 1.5rem;
		border-radius: 0.75rem;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
		margin-bottom: 1.5rem;
	}

	.section h2 {
		margin: 0 0 1.5rem 0;
		font-size: 1.25rem;
		color: #2c3e50;
	}

	.step-header,
	.result-header {
		display: flex;
		align-items: center;
		gap: 1rem;
		margin-bottom: 1.5rem;
	}

	.back-btn {
		background: white;
		border: 2px solid #e0e0e0;
		padding: 0.5rem 1rem;
		border-radius: 0.5rem;
		cursor: pointer;
		font-weight: 600;
		color: #666;
		transition: all 0.3s ease;
	}

	.back-btn:hover {
		border-color: #667eea;
		color: #667eea;
		background: #f9fafb;
	}

	.stores-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
		gap: 1rem;
	}

	.store-card {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.75rem;
		padding: 1.25rem;
		background: linear-gradient(135deg, #f9fafb 0%, #f3f4f6 100%);
		border: 2px solid #e0e0e0;
		border-radius: 0.75rem;
		cursor: pointer;
		transition: all 0.3s ease;
		text-align: center;
		font-weight: 600;
	}

	.store-card:hover {
		transform: translateY(-4px);
		border-color: #667eea;
		background: linear-gradient(135deg, #f0f4ff 0%, #e8ecff 100%);
		box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
	}

	.store-icon {
		font-size: 2.5rem;
		line-height: 1;
	}

	.store-name {
		color: #2c3e50;
		font-size: 1rem;
	}

	.store-number {
		color: #667eea;
		font-size: 0.9rem;
	}

	.store-location {
		font-size: 0.85rem;
		color: #999;
		font-weight: 400;
	}

	.empty-state {
		text-align: center;
		padding: 2rem;
		color: #999;
		grid-column: 1 / -1;
	}

	.audit-form {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.form-group {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.form-group label {
		font-weight: 600;
		color: #2c3e50;
	}

	.required {
		color: #e74c3c;
	}

	.form-group input,
	.form-group select {
		padding: 0.75rem;
		border: 2px solid #e0e0e0;
		border-radius: 0.5rem;
		font-size: 1rem;
		font-family: inherit;
		transition: border-color 0.3s ease;
	}

	.form-group input:focus,
	.form-group select:focus {
		outline: none;
		border-color: #667eea;
		box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
	}

	.input-group {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.input-group input {
		flex: 1;
	}

	.unit {
		color: #999;
		font-size: 0.9rem;
		font-weight: 400;
		min-width: 50px;
	}

	.help-text {
		font-size: 0.85rem;
		color: #999;
		margin-top: 0.25rem;
	}

	.btn-primary {
		padding: 1rem;
		background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
		color: white;
		border: none;
		border-radius: 0.5rem;
		font-weight: 700;
		font-size: 1rem;
		cursor: pointer;
		transition: all 0.3s ease;
		margin-top: 0.5rem;
	}

	.btn-primary:hover {
		transform: translateY(-2px);
		box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
	}

	.status-alert {
		display: flex;
		gap: 1rem;
		padding: 1.25rem;
		background: #f9fafb;
		border-left: 4px solid;
		border-radius: 0.5rem;
		margin-bottom: 1.5rem;
		align-items: flex-start;
	}

	.alert-icon {
		font-size: 1.75rem;
		line-height: 1;
		flex-shrink: 0;
	}

	.alert-content {
		flex: 1;
	}

	.alert-title {
		font-weight: 700;
		color: #2c3e50;
		margin-bottom: 0.25rem;
	}

	.alert-message {
		color: #555;
		font-size: 0.95rem;
		line-height: 1.4;
	}

	.metrics-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
		gap: 1rem;
		margin-bottom: 1.5rem;
	}

	.metric {
		text-align: center;
		padding: 1rem;
		background: linear-gradient(135deg, #f9fafb 0%, #f3f4f6 100%);
		border-radius: 0.5rem;
		border: 1px solid #e0e0e0;
	}

	.metric-label {
		font-size: 0.85rem;
		color: #999;
		text-transform: uppercase;
		margin-bottom: 0.5rem;
	}

	.metric-value {
		font-size: 2rem;
		font-weight: 700;
		line-height: 1;
		margin-bottom: 0.25rem;
	}

	.metric-unit {
		font-size: 0.75rem;
		color: #999;
	}

	.info-section {
		margin: 1.5rem 0;
	}

	.info-section h3 {
		margin: 0 0 1rem 0;
		font-size: 1rem;
		color: #2c3e50;
	}

	.info-grid {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.info-row {
		display: flex;
		justify-content: space-between;
		padding: 0.75rem;
		background: linear-gradient(135deg, #f9fafb 0%, #f3f4f6 100%);
		border-radius: 0.4rem;
		border: 1px solid #e0e0e0;
	}

	.info-row .label {
		font-weight: 600;
		color: #666;
	}

	.info-row .value {
		color: #2c3e50;
		font-weight: 600;
	}

	.recommendation {
		display: flex;
		gap: 1rem;
		padding: 1.25rem;
		border-radius: 0.5rem;
		margin-bottom: 1.5rem;
		align-items: flex-start;
	}

	.recommendation.critical {
		background: #fadbd8;
		border-left: 4px solid #e74c3c;
	}

	.recommendation.warning {
		background: #fef5e7;
		border-left: 4px solid #f39c12;
	}

	.recommendation.success {
		background: #d5f4e6;
		border-left: 4px solid #27ae60;
	}

	.rec-icon {
		font-size: 1.5rem;
		line-height: 1;
		flex-shrink: 0;
	}

	.rec-content {
		flex: 1;
	}

	.rec-title {
		font-weight: 700;
		color: #2c3e50;
		margin-bottom: 0.25rem;
	}

	.rec-text {
		color: #555;
		font-size: 0.95rem;
		line-height: 1.4;
	}

	.email-status {
		display: inline-block;
		margin-top: 0.75rem;
		padding: 0.5rem 0.75rem;
		background: rgba(0, 0, 0, 0.1);
		border-radius: 0.4rem;
		font-size: 0.85rem;
		color: #27ae60;
		font-weight: 600;
	}

	.btn-email {
		display: inline-block;
		margin-top: 0.75rem;
		padding: 0.5rem 0.75rem;
		background: white;
		border: 2px solid #e74c3c;
		color: #e74c3c;
		border-radius: 0.4rem;
		cursor: pointer;
		font-weight: 600;
		transition: all 0.3s ease;
	}

	.btn-email:hover {
		background: #e74c3c;
		color: white;
		transform: translateY(-2px);
	}

	.action-buttons {
		display: flex;
		gap: 1rem;
		flex-wrap: wrap;
	}

	.btn-critical {
		flex: 1;
		min-width: 200px;
		padding: 1rem;
		background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
		color: white;
		border: none;
		border-radius: 0.5rem;
		font-weight: 700;
		font-size: 1rem;
		cursor: pointer;
		transition: all 0.3s ease;
		animation: pulse 2s infinite;
	}

	.btn-critical:hover:not(:disabled) {
		transform: translateY(-2px);
		box-shadow: 0 4px 12px rgba(231, 76, 60, 0.4);
	}

	.btn-critical:disabled {
		opacity: 0.7;
		cursor: not-allowed;
	}

	.btn-secondary {
		flex: 1;
		min-width: 150px;
		padding: 1rem;
		background: white;
		color: #667eea;
		border: 2px solid #667eea;
		border-radius: 0.5rem;
		font-weight: 700;
		font-size: 1rem;
		cursor: pointer;
		transition: all 0.3s ease;
	}

	.btn-secondary:hover {
		background: #667eea;
		color: white;
		transform: translateY(-2px);
	}

	@keyframes pulse {
		0%, 100% {
			opacity: 1;
		}
		50% {
			opacity: 0.85;
		}
	}

	@media (max-width: 640px) {
		.audit-container {
			padding: 0.75rem;
		}

		.stores-grid {
			grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
		}

		.metrics-grid {
			grid-template-columns: repeat(2, 1fr);
		}

		.action-buttons {
			flex-direction: column;
		}

		.btn-critical,
		.btn-secondary {
			min-width: auto;
		}
	}
</style>
