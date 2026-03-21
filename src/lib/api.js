/**
 * API utilities for dashboard components
 * Provides mock data and API endpoints for Dashboard, MyCustomers, and AuditStore
 */

// Mock data generators
const MOCK_REPS = [
	{
		id: '8548368719',
		name: 'Tyler Van Sant',
		base_location: 'Ridgefield, WA',
		role: 'manager',
		searches: 48,
		saved_prospects: 12,
		closed_deals: 3,
		interested: 4,
		followup: 5,
		proposal: 2,
		closed: 1,
		monthly_score: 92,
		yearly_score: 87
	},
	{
		id: '8703124669',
		name: 'Meghan Wink',
		base_location: 'Vancouver, WA',
		role: 'rep',
		searches: 35,
		saved_prospects: 8,
		closed_deals: 2,
		interested: 3,
		followup: 3,
		proposal: 1,
		closed: 1,
		monthly_score: 78,
		yearly_score: 75
	},
	{
		id: '8003974335',
		name: 'Marty',
		base_location: 'Newberg, OR',
		role: 'rep',
		searches: 42,
		saved_prospects: 10,
		closed_deals: 2,
		interested: 4,
		followup: 4,
		proposal: 1,
		closed: 1,
		monthly_score: 85,
		yearly_score: 82
	},
	{
		id: '7334094238',
		name: 'Rick Diamond',
		base_location: 'Portland, OR',
		role: 'rep',
		searches: 28,
		saved_prospects: 6,
		closed_deals: 1,
		interested: 2,
		followup: 2,
		proposal: 1,
		closed: 1,
		monthly_score: 68,
		yearly_score: 72
	}
];

const MOCK_PROSPECTS = [
	{
		id: 'db9193785c0c',
		name: 'Autotek International',
		address: '2430 SE Umatilla St, Portland',
		phone: '(503) 454-6141',
		email: 'contact@autotek.com',
		contact_name: 'John Smith',
		score: 68.8,
		status: 'closed',
		saved_date: '2026-03-03T15:38:19.820599',
		last_contacted: '2026-03-15T10:00:00',
		visit_count: 3,
		notes: [
			{
				text: 'Successfully closed deal on March 15',
				date: '2026-03-15T10:00:00'
			}
		]
	},
	{
		id: '3738e11b7287',
		name: "Papa Murphy's | Take 'N' Bake Pizza",
		address: '945 Washington Way, Longview',
		phone: '(360) 577-0696',
		email: 'manager@papamurphys.com',
		contact_name: 'Sarah Johnson',
		score: 66.2,
		status: 'follow-up',
		saved_date: '2026-03-05T14:52:37.888951',
		last_contacted: null,
		visit_count: 1,
		notes: [
			{
				text: 'Initial contact made, needs follow-up',
				date: '2026-03-05T14:52:37'
			}
		]
	},
	{
		id: '6c91920ee839',
		name: 'ZENSHI Handcrafted Sushi',
		address: '33702 21st Ave SW, Federal Way',
		phone: '+1 253-952-0108',
		email: 'info@zenshi-sushi.com',
		contact_name: 'David Chen',
		score: 39,
		status: 'interested',
		saved_date: '2026-03-17T09:25:02.940112',
		last_contacted: null,
		visit_count: 0,
		notes: []
	},
	{
		id: 'da5085fe23b7',
		name: 'Crown Plaza Hotel',
		address: '1319 116th Ave NE, Bellevue',
		phone: '(425) 455-3800',
		email: 'procurement@crownplaza.com',
		contact_name: 'Lisa Wong',
		score: 72.5,
		status: 'proposal',
		saved_date: '2026-03-10T11:20:00',
		last_contacted: '2026-03-18T14:30:00',
		visit_count: 2,
		notes: [
			{
				text: 'Sent proposal for tape supply contract',
				date: '2026-03-18T14:30:00'
			},
			{
				text: 'Waiting for decision by end of week',
				date: '2026-03-19T09:00:00'
			}
		]
	},
	{
		id: 'abc123def456',
		name: 'Seattle Medical Center',
		address: '1959 NE Pacific St, Seattle',
		phone: '(206) 987-2000',
		email: 'supplies@smc.org',
		contact_name: 'Michael Brown',
		score: 55.3,
		status: 'follow-up',
		saved_date: '2026-03-12T13:45:00',
		last_contacted: '2026-03-19T10:15:00',
		visit_count: 1,
		notes: [
			{
				text: 'Expressed interest in bulk ordering',
				date: '2026-03-19T10:15:00'
			}
		]
	}
];

const MOCK_STORES = [
	{
		number: 'PDX-001',
		name: 'Portland Main',
		location: 'Portland, OR',
		manager: 'Tyler Van Sant'
	},
	{
		number: 'VAN-002',
		name: 'Vancouver Hub',
		location: 'Vancouver, WA',
		manager: 'Meghan Wink'
	},
	{
		number: 'ORE-003',
		name: 'Newberg Location',
		location: 'Newberg, OR',
		manager: 'Marty'
	},
	{
		number: 'PDX-004',
		name: 'Portland South',
		location: 'Portland, OR',
		manager: 'Rick Diamond'
	}
];

/**
 * Dashboard API endpoints
 */
export const dashboardAPI = {
	async getMetrics() {
		// Simulate API delay
		await new Promise(resolve => setTimeout(resolve, 500));
		
		return {
			reps: MOCK_REPS,
			timestamp: new Date().toISOString()
		};
	}
};

/**
 * Customers API endpoints
 */
export const customersAPI = {
	async getProspects() {
		// Simulate API delay
		await new Promise(resolve => setTimeout(resolve, 300));
		
		return {
			prospects: MOCK_PROSPECTS,
			timestamp: new Date().toISOString()
		};
	},

	async addNote(prospectId, noteText) {
		// Simulate API delay
		await new Promise(resolve => setTimeout(resolve, 200));
		
		return {
			success: true,
			prospect_id: prospectId,
			note: {
				text: noteText,
				date: new Date().toISOString()
			}
		};
	},

	async quickAction(prospectId, action) {
		// Simulate API delay
		await new Promise(resolve => setTimeout(resolve, 300));
		
		const actionMap = {
			call: 'Initiated call',
			email: 'Email sent',
			note: 'Note saved'
		};

		return {
			success: true,
			prospect_id: prospectId,
			action: action,
			message: actionMap[action] || 'Action completed',
			timestamp: new Date().toISOString()
		};
	}
};

/**
 * Audit Store API endpoints
 */
export const auditAPI = {
	async getStores() {
		// Simulate API delay
		await new Promise(resolve => setTimeout(resolve, 300));
		
		return {
			stores: MOCK_STORES,
			timestamp: new Date().toISOString()
		};
	},

	async calculateAudit(inventoryData) {
		// Simulate API delay
		await new Promise(resolve => setTimeout(resolve, 400));
		
		const {
			starting_cases = 20,
			units_per_roll = 4,
			rolls_per_case = 12,
			current_rolls = 0,
			delivery_date,
			cycle = '5-day'
		} = inventoryData;

		// Calculate metrics
		const total_rolls = current_rolls;
		const total_units = total_rolls * units_per_roll;
		
		// Determine daily usage based on cycle
		const cycleUsage = {
			'3-day': 4,
			'5-day': 2.5,
			'7-day': 1.8,
			'custom': 2.5
		};
		const daily_usage = cycleUsage[cycle] || 2.5;
		
		// Calculate days until runout
		const days_until_runout = total_rolls / daily_usage;
		
		// Calculate days until delivery
		const today = new Date();
		const delivery = new Date(delivery_date);
		const days_until_delivery = Math.ceil((delivery - today) / (1000 * 60 * 60 * 24));
		
		// Determine status
		let status = 'SUFFICIENT';
		let message = 'You have enough inventory to cover the delivery cycle.';
		
		if (days_until_runout <= days_until_delivery) {
			status = 'INSUFFICIENT';
			message = `ALERT: Inventory will run out in ${days_until_runout.toFixed(1)} days, but delivery is in ${days_until_delivery} days. Action required!`;
		} else if (days_until_runout < days_until_delivery + 2) {
			status = 'WARNING';
			message = 'Warning: Inventory is running close to the delivery date. Monitor usage.';
		}

		return {
			status,
			message,
			total_rolls,
			total_units,
			daily_usage: parseFloat(daily_usage.toFixed(2)),
			days_until_runout: parseFloat(days_until_runout.toFixed(1)),
			days_until_delivery,
			store_num: inventoryData.store_num,
			email_sent: false,
			timestamp: new Date().toISOString()
		};
	},

	async sendAuditEmail(storeNum, auditResult) {
		// Simulate API delay
		await new Promise(resolve => setTimeout(resolve, 500));
		
		return {
			success: true,
			email_sent: true,
			recipient: 'tyler.vansant@indoormedia.com',
			subject: `CRITICAL: Store ${storeNum} Low Inventory Alert`,
			timestamp: new Date().toISOString()
		};
	}
};

/**
 * Global fetch wrapper for API calls
 */
export async function apiCall(endpoint, options = {}) {
	const { method = 'GET', body = null } = options;
	
	try {
		const response = await fetch(endpoint, {
			method,
			headers: {
				'Content-Type': 'application/json',
				...options.headers
			},
			body: body ? JSON.stringify(body) : undefined
		});

		if (!response.ok) {
			throw new Error(`API error: ${response.status}`);
		}

		return await response.json();
	} catch (error) {
		console.error(`API call failed: ${endpoint}`, error);
		throw error;
	}
}
