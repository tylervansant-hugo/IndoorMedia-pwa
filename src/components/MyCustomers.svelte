<script>
	import { onMount } from 'svelte';

	let prospects = [];
	let filteredProspects = [];
	let selectedStatus = 'all'; // 'all', 'interested', 'follow-up', 'proposal', 'closed'
	let searchQuery = '';
	let loading = true;
	let error = null;
	let selectedProspect = null;
	let showNoteModal = false;
	let noteText = '';

	const statusOptions = [
		{ value: 'all', label: 'All', icon: '👥' },
		{ value: 'interested', label: 'Interested', icon: '👀' },
		{ value: 'follow-up', label: 'Follow-up', icon: '📞' },
		{ value: 'proposal', label: 'Proposal', icon: '📄' },
		{ value: 'closed', label: 'Closed', icon: '✅' }
	];

	onMount(async () => {
		try {
			const response = await fetch('/api/customers/prospects');
			if (!response.ok) throw new Error('Failed to load prospects');
			const data = await response.json();
			prospects = data.prospects || [];
			applyFilters();
			loading = false;
		} catch (err) {
			error = err.message;
			loading = false;
		}
	});

	function applyFilters() {
		let filtered = prospects;

		// Apply status filter
		if (selectedStatus !== 'all') {
			filtered = filtered.filter(p => p.status === selectedStatus);
		}

		// Apply search filter
		if (searchQuery.trim()) {
			const query = searchQuery.toLowerCase();
			filtered = filtered.filter(
				p =>
					p.name.toLowerCase().includes(query) ||
					p.address.toLowerCase().includes(query) ||
					p.phone.toLowerCase().includes(query)
			);
		}

		filteredProspects = filtered;
	}

	function handleStatusChange(status) {
		selectedStatus = status;
		applyFilters();
	}

	function handleSearch(e) {
		searchQuery = e.target.value;
		applyFilters();
	}

	function selectProspect(prospect) {
		selectedProspect = prospect;
	}

	function closeProspectDetail() {
		selectedProspect = null;
		noteText = '';
	}

	function openNoteModal() {
		showNoteModal = true;
		noteText = '';
	}

	function closeNoteModal() {
		showNoteModal = false;
		noteText = '';
	}

	async function saveNote() {
		if (!selectedProspect || !noteText.trim()) return;

		try {
			const response = await fetch(`/api/customers/note`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					prospect_id: selectedProspect.id,
					note: noteText
				})
			});

			if (response.ok) {
				selectedProspect.notes = selectedProspect.notes || [];
				selectedProspect.notes.unshift({
					text: noteText,
					date: new Date().toISOString()
				});
				closeNoteModal();
			}
		} catch (err) {
			console.error('Error saving note:', err);
		}
	}

	async function quickAction(action) {
		if (!selectedProspect) return;

		try {
			const response = await fetch(`/api/customers/action`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					prospect_id: selectedProspect.id,
					action: action
				})
			});

			if (response.ok) {
				closeProspectDetail();
			}
		} catch (err) {
			console.error(`Error with ${action}:`, err);
		}
	}

	function getStatusColor(status) {
		const colors = {
			interested: '#f39c12',
			'follow-up': '#3498db',
			proposal: '#9b59b6',
			closed: '#27ae60'
		};
		return colors[status] || '#95a5a6';
	}

	function getStatusIcon(status) {
		const icons = {
			interested: '👀',
			'follow-up': '📞',
			proposal: '📄',
			closed: '✅'
		};
		return icons[status] || '📌';
	}

	$: statusCount = {
		all: prospects.length,
		interested: prospects.filter(p => p.status === 'interested').length,
		'follow-up': prospects.filter(p => p.status === 'follow-up').length,
		proposal: prospects.filter(p => p.status === 'proposal').length,
		closed: prospects.filter(p => p.status === 'closed').length
	};
</script>

<div class="customers-container">
	<div class="header">
		<h1>👥 My Customers</h1>
		<div class="search-bar">
			<input
				type="text"
				placeholder="Search by name, address, phone..."
				value={searchQuery}
				on:input={handleSearch}
			/>
		</div>
	</div>

	{#if loading}
		<div class="loading">Loading prospects...</div>
	{:else if error}
		<div class="error">Error: {error}</div>
	{:else}
		<!-- Status Filter Tabs -->
		<div class="status-tabs">
			{#each statusOptions as option (option.value)}
				<button
					class="status-tab"
					class:active={selectedStatus === option.value}
					on:click={() => handleStatusChange(option.value)}
				>
					<span class="icon">{option.icon}</span>
					<span class="label">{option.label}</span>
					<span class="count">{statusCount[option.value]}</span>
				</button>
			{/each}
		</div>

		<!-- Prospects List -->
		<div class="prospects-list">
			{#if filteredProspects.length === 0}
				<div class="empty-state">
					<div class="empty-icon">🔍</div>
					<p>No prospects found</p>
					<p class="empty-subtitle">Try adjusting your filters or search query</p>
				</div>
			{:else}
				{#each filteredProspects as prospect (prospect.id)}
					<div
						class="prospect-card"
						on:click={() => selectProspect(prospect)}
						on:keydown={(e) => e.key === 'Enter' && selectProspect(prospect)}
						role="button"
						tabindex="0"
					>
						<div class="prospect-header">
							<div class="prospect-name">{prospect.name || 'Unknown'}</div>
							<div class="status-badge" style="background-color: {getStatusColor(prospect.status)}">
								{getStatusIcon(prospect.status)} {prospect.status}
							</div>
						</div>

						<div class="prospect-body">
							<div class="prospect-info">
								<span class="info-item">📍 {prospect.address}</span>
								<span class="info-item">📞 {prospect.phone}</span>
								{#if prospect.email}
									<span class="info-item">✉️ {prospect.email}</span>
								{/if}
							</div>

							<div class="prospect-meta">
								<span class="meta-item">Score: {prospect.score || 0}%</span>
								<span class="meta-item">Saved: {new Date(prospect.saved_date).toLocaleDateString()}</span>
								{#if prospect.last_contacted}
									<span class="meta-item"
										>Last Contact: {new Date(prospect.last_contacted).toLocaleDateString()}</span
									>
								{/if}
							</div>
						</div>

						<div class="prospect-footer">
							<span class="action-hint">→ View Details</span>
						</div>
					</div>
				{/each}
			{/if}
		</div>
	{/if}

	<!-- Prospect Detail Modal -->
	{#if selectedProspect}
		<div class="modal-backdrop" on:click={closeProspectDetail}>
			<div class="modal" on:click|stopPropagation>
				<div class="modal-header">
					<h2>{selectedProspect.name}</h2>
					<button class="close-btn" on:click={closeProspectDetail}>✕</button>
				</div>

				<div class="modal-body">
					<!-- Prospect Info -->
					<div class="info-section">
						<h3>Contact Information</h3>
						<div class="info-grid">
							<div class="info-row">
								<span class="label">📍 Address</span>
								<span class="value">{selectedProspect.address || 'N/A'}</span>
							</div>
							<div class="info-row">
								<span class="label">📞 Phone</span>
								<span class="value">{selectedProspect.phone || 'N/A'}</span>
							</div>
							<div class="info-row">
								<span class="label">✉️ Email</span>
								<span class="value">{selectedProspect.email || 'N/A'}</span>
							</div>
							<div class="info-row">
								<span class="label">👤 Contact Name</span>
								<span class="value">{selectedProspect.contact_name || 'N/A'}</span>
							</div>
						</div>
					</div>

					<!-- Prospect Stats -->
					<div class="stats-section">
						<h3>Statistics</h3>
						<div class="stats-grid">
							<div class="stat-card">
								<div class="stat-label">Status</div>
								<div class="stat-value">
									<span
										class="status-badge"
										style="background-color: {getStatusColor(selectedProspect.status)}"
									>
										{getStatusIcon(selectedProspect.status)}
										{selectedProspect.status}
									</span>
								</div>
							</div>
							<div class="stat-card">
								<div class="stat-label">Score</div>
								<div class="stat-value">{selectedProspect.score || 0}%</div>
							</div>
							<div class="stat-card">
								<div class="stat-label">Visits</div>
								<div class="stat-value">{selectedProspect.visit_count || 0}</div>
							</div>
							<div class="stat-card">
								<div class="stat-label">Saved Date</div>
								<div class="stat-value">{new Date(selectedProspect.saved_date).toLocaleDateString()}</div>
							</div>
						</div>
					</div>

					<!-- Notes Section -->
					{#if selectedProspect.notes && selectedProspect.notes.length > 0}
						<div class="notes-section">
							<h3>📝 Notes</h3>
							<div class="notes-list">
								{#each selectedProspect.notes as note (note.date)}
									<div class="note-item">
										<div class="note-date">{new Date(note.date).toLocaleDateString()}</div>
										<div class="note-text">{note.text}</div>
									</div>
								{/each}
							</div>
						</div>
					{/if}
				</div>

				<div class="modal-footer">
					<button class="action-btn call" on:click={() => quickAction('call')}>
						📞 Call
					</button>
					<button class="action-btn email" on:click={() => quickAction('email')}>
						✉️ Email
					</button>
					<button class="action-btn note" on:click={openNoteModal}>
						📝 Add Note
					</button>
				</div>
			</div>
		</div>
	{/if}

	<!-- Note Modal -->
	{#if showNoteModal}
		<div class="modal-backdrop" on:click={closeNoteModal}>
			<div class="modal modal-small" on:click|stopPropagation>
				<div class="modal-header">
					<h2>Add Note</h2>
					<button class="close-btn" on:click={closeNoteModal}>✕</button>
				</div>

				<div class="modal-body">
					<textarea
						placeholder="Enter your note..."
						bind:value={noteText}
						class="note-textarea"
					/>
				</div>

				<div class="modal-footer">
					<button class="btn-secondary" on:click={closeNoteModal}>Cancel</button>
					<button class="btn-primary" on:click={saveNote} disabled={!noteText.trim()}>
						Save Note
					</button>
				</div>
			</div>
		</div>
	{/if}
</div>

<style>
	.customers-container {
		padding: 1rem;
		padding-bottom: calc(120px + env(safe-area-inset-bottom, 0px));
		background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
		min-height: 100vh;
	}

	.header {
		margin-bottom: 1.5rem;
	}

	.header h1 {
		margin: 0 0 1rem 0;
		font-size: 1.5rem;
		color: #2c3e50;
	}

	.search-bar {
		display: flex;
		gap: 0.5rem;
	}

	.search-bar input {
		flex: 1;
		padding: 0.75rem 1rem;
		border: 2px solid #e0e0e0;
		border-radius: 0.5rem;
		font-size: 1rem;
		transition: all 0.3s ease;
		background: white;
	}

	.search-bar input:focus {
		outline: none;
		border-color: #667eea;
		box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
	}

	.status-tabs {
		display: flex;
		gap: 0.75rem;
		margin-bottom: 1.5rem;
		overflow-x: auto;
		padding-bottom: 0.5rem;
	}

	.status-tab {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.5rem 1rem;
		background: white;
		border: 2px solid #e0e0e0;
		border-radius: 0.5rem;
		cursor: pointer;
		white-space: nowrap;
		transition: all 0.3s ease;
		font-weight: 600;
	}

	.status-tab:hover {
		border-color: #667eea;
		color: #667eea;
	}

	.status-tab.active {
		background: #667eea;
		color: white;
		border-color: #667eea;
	}

	.status-tab .icon {
		font-size: 1.25rem;
		line-height: 1;
	}

	.status-tab .count {
		display: inline-block;
		background: rgba(0, 0, 0, 0.1);
		padding: 0.125rem 0.5rem;
		border-radius: 1rem;
		font-size: 0.875rem;
	}

	.status-tab.active .count {
		background: rgba(255, 255, 255, 0.3);
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

	.prospects-list {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.empty-state {
		text-align: center;
		padding: 3rem 1rem;
		background: white;
		border-radius: 0.75rem;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
	}

	.empty-icon {
		font-size: 3rem;
		margin-bottom: 1rem;
	}

	.empty-state p {
		margin: 0 0 0.5rem 0;
		color: #2c3e50;
		font-weight: 600;
	}

	.empty-subtitle {
		color: #999;
		font-size: 0.875rem;
	}

	.prospect-card {
		background: white;
		border-radius: 0.75rem;
		overflow: hidden;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
		transition: all 0.3s ease;
		cursor: pointer;
	}

	.prospect-card:hover {
		transform: translateY(-4px);
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
	}

	.prospect-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 1rem;
		background: linear-gradient(135deg, #f9fafb 0%, #f3f4f6 100%);
		border-bottom: 2px solid #e0e0e0;
	}

	.prospect-name {
		font-weight: 700;
		font-size: 1.1rem;
		color: #2c3e50;
	}

	.status-badge {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.35rem 0.75rem;
		border-radius: 1rem;
		color: white;
		font-size: 0.85rem;
		font-weight: 600;
		white-space: nowrap;
	}

	.prospect-body {
		padding: 1rem;
	}

	.prospect-info {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		margin-bottom: 0.75rem;
	}

	.info-item {
		font-size: 0.9rem;
		color: #555;
	}

	.prospect-meta {
		display: flex;
		flex-wrap: wrap;
		gap: 1rem;
		font-size: 0.8rem;
		color: #999;
	}

	.meta-item {
		display: inline-block;
	}

	.prospect-footer {
		padding: 0.75rem 1rem;
		background: #f9fafb;
		border-top: 1px solid #e0e0e0;
		text-align: right;
		font-size: 0.85rem;
		color: #667eea;
		font-weight: 600;
	}

	.action-hint {
		display: inline-flex;
		align-items: center;
		gap: 0.25rem;
	}

	/* Modal Styles */
	.modal-backdrop {
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		bottom: 0;
		background: rgba(0, 0, 0, 0.5);
		display: flex;
		align-items: flex-end;
		justify-content: center;
		z-index: 1000;
		padding: 1rem;
	}

	.modal {
		background: white;
		border-radius: 1rem 1rem 0 0;
		width: 100%;
		max-width: 500px;
		max-height: 90vh;
		display: flex;
		flex-direction: column;
		box-shadow: 0 -4px 16px rgba(0, 0, 0, 0.2);
		animation: slideUp 0.3s ease;
	}

	.modal-small {
		max-width: 400px;
		max-height: 60vh;
	}

	@keyframes slideUp {
		from {
			transform: translateY(100%);
		}
		to {
			transform: translateY(0);
		}
	}

	.modal-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 1.5rem;
		border-bottom: 2px solid #e0e0e0;
	}

	.modal-header h2 {
		margin: 0;
		font-size: 1.25rem;
		color: #2c3e50;
	}

	.close-btn {
		background: none;
		border: none;
		font-size: 1.5rem;
		cursor: pointer;
		color: #999;
		padding: 0;
		line-height: 1;
		transition: color 0.3s ease;
	}

	.close-btn:hover {
		color: #2c3e50;
	}

	.modal-body {
		flex: 1;
		overflow-y: auto;
		padding: 1.5rem;
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.info-section,
	.stats-section,
	.notes-section {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.info-section h3,
	.stats-section h3,
	.notes-section h3 {
		margin: 0 0 0.75rem 0;
		font-size: 1rem;
		color: #2c3e50;
		font-weight: 700;
	}

	.info-grid {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.info-row {
		display: flex;
		align-items: flex-start;
		gap: 1rem;
	}

	.info-row .label {
		min-width: 100px;
		font-weight: 600;
		color: #666;
	}

	.info-row .value {
		flex: 1;
		color: #2c3e50;
	}

	.stats-grid {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: 0.75rem;
	}

	.stat-card {
		padding: 0.75rem;
		background: #f9fafb;
		border-radius: 0.5rem;
		border: 1px solid #e0e0e0;
	}

	.stat-label {
		font-size: 0.75rem;
		color: #999;
		text-transform: uppercase;
		margin-bottom: 0.25rem;
	}

	.stat-value {
		font-size: 1.1rem;
		font-weight: 700;
		color: #2c3e50;
	}

	.notes-list {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.note-item {
		padding: 0.75rem;
		background: #f9fafb;
		border-left: 3px solid #667eea;
		border-radius: 0.4rem;
	}

	.note-date {
		font-size: 0.75rem;
		color: #999;
		margin-bottom: 0.25rem;
	}

	.note-text {
		color: #2c3e50;
		font-size: 0.9rem;
		line-height: 1.4;
	}

	.note-textarea {
		width: 100%;
		min-height: 120px;
		padding: 0.75rem;
		border: 2px solid #e0e0e0;
		border-radius: 0.5rem;
		font-family: inherit;
		font-size: 1rem;
		resize: vertical;
		transition: border-color 0.3s ease;
	}

	.note-textarea:focus {
		outline: none;
		border-color: #667eea;
		box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
	}

	.modal-footer {
		display: flex;
		gap: 0.75rem;
		padding: 1.5rem;
		border-top: 2px solid #e0e0e0;
		background: #f9fafb;
	}

	.action-btn {
		flex: 1;
		padding: 0.75rem 1rem;
		border: none;
		border-radius: 0.5rem;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.3s ease;
		font-size: 0.9rem;
	}

	.action-btn.call {
		background: #3498db;
		color: white;
	}

	.action-btn.call:hover {
		background: #2980b9;
		transform: translateY(-2px);
	}

	.action-btn.email {
		background: #9b59b6;
		color: white;
	}

	.action-btn.email:hover {
		background: #8e44ad;
		transform: translateY(-2px);
	}

	.action-btn.note {
		background: #f39c12;
		color: white;
	}

	.action-btn.note:hover {
		background: #e67e22;
		transform: translateY(-2px);
	}

	.btn-primary,
	.btn-secondary {
		flex: 1;
		padding: 0.75rem 1rem;
		border: none;
		border-radius: 0.5rem;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.3s ease;
	}

	.btn-primary {
		background: #667eea;
		color: white;
	}

	.btn-primary:hover:not(:disabled) {
		background: #5568d3;
		transform: translateY(-2px);
	}

	.btn-primary:disabled {
		background: #ccc;
		cursor: not-allowed;
	}

	.btn-secondary {
		background: white;
		color: #2c3e50;
		border: 2px solid #e0e0e0;
	}

	.btn-secondary:hover {
		border-color: #667eea;
		color: #667eea;
	}

	@media (max-width: 640px) {
		.customers-container {
			padding: 0.75rem;
		}

		.modal {
			border-radius: 1rem;
			max-height: 80vh;
			margin: 1rem;
		}

		.stats-grid {
			grid-template-columns: 1fr;
		}

		.status-tabs {
			gap: 0.5rem;
		}

		.status-tab {
			padding: 0.4rem 0.8rem;
			font-size: 0.85rem;
		}

		.modal-footer {
			flex-wrap: wrap;
		}

		.action-btn {
			flex: 0 1 calc(33.333% - 0.5rem);
		}
	}
</style>
