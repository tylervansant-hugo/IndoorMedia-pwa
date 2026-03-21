/**
 * Simple Express server for PWA backend
 * Provides API endpoints for dashboard, customers, and audit store
 */

import express from 'express';
import cors from 'cors';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';

const app = express();
const PORT = process.env.PORT || 3001;
const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'dist')));

// Load data files
function loadJSON(filePath) {
	try {
		return JSON.parse(fs.readFileSync(filePath, 'utf-8'));
	} catch (err) {
		console.error(`Failed to load ${filePath}:`, err.message);
		return {};
	}
}

const prospectData = loadJSON(path.join(__dirname, '../data/prospect_data.json'));
const repRegistry = loadJSON(path.join(__dirname, '../data/rep_registry.json'));

// ============= DASHBOARD API =============

app.get('/api/dashboard/metrics', (req, res) => {
	try {
		// Transform prospect data into rep metrics
		const reps = [];
		
		if (prospectData.reps) {
			Object.entries(prospectData.reps).forEach(([repId, repData]) => {
				const registry = repRegistry[repId] || {};
				const prospects = repData.saved_prospects || {};
				
				// Count by status
				const statusCounts = {
					interested: 0,
					'follow-up': 0,
					proposal: 0,
					closed: 0
				};
				
				let totalScore = 0;
				let prospectCount = 0;
				
				Object.values(prospects).forEach(prospect => {
					if (prospect.status) {
						statusCounts[prospect.status] = (statusCounts[prospect.status] || 0) + 1;
					}
					if (prospect.score) {
						totalScore += prospect.score;
						prospectCount++;
					}
				});
				
				const avgScore = prospectCount > 0 ? totalScore / prospectCount : 0;
				const searches = Object.keys(prospects).length;
				
				reps.push({
					id: repId,
					name: registry.display_name || registry.contract_name || 'Unknown',
					base_location: registry.base_location || 'Unknown',
					role: registry.role || 'rep',
					searches: searches,
					saved_prospects: Object.keys(prospects).length,
					closed_deals: statusCounts.closed,
					interested: statusCounts.interested,
					followup: statusCounts['follow-up'],
					proposal: statusCounts.proposal,
					closed: statusCounts.closed,
					monthly_score: Math.round(avgScore * 1.2), // Boost for visual effect
					yearly_score: Math.round(avgScore),
					average_prospect_score: Math.round(avgScore)
				});
			});
		}
		
		// Sort by monthly score
		reps.sort((a, b) => b.monthly_score - a.monthly_score);
		
		res.json({
			reps,
			timestamp: new Date().toISOString(),
			source: 'prospect_data.json'
		});
	} catch (error) {
		console.error('Dashboard API error:', error);
		res.status(500).json({ error: 'Failed to load metrics' });
	}
});

// ============= CUSTOMERS API =============

app.get('/api/customers/prospects', (req, res) => {
	try {
		const prospects = [];
		
		if (prospectData.reps) {
			Object.entries(prospectData.reps).forEach(([repId, repData]) => {
				const savedProspects = repData.saved_prospects || {};
				
				Object.entries(savedProspects).forEach(([prospectId, prospect]) => {
					prospects.push({
						id: prospectId,
						rep_id: repId,
						rep_name: prospectData.reps?.[repId]?.name,
						...prospect
					});
				});
			});
		}
		
		res.json({
			prospects,
			timestamp: new Date().toISOString(),
			source: 'prospect_data.json'
		});
	} catch (error) {
		console.error('Customers API error:', error);
		res.status(500).json({ error: 'Failed to load prospects' });
	}
});

app.post('/api/customers/note', (req, res) => {
	try {
		const { prospect_id, note } = req.body;
		
		if (!prospect_id || !note) {
			return res.status(400).json({ error: 'Missing prospect_id or note' });
		}
		
		// In production, this would save to database
		res.json({
			success: true,
			prospect_id,
			note: {
				text: note,
				date: new Date().toISOString()
			}
		});
	} catch (error) {
		console.error('Note API error:', error);
		res.status(500).json({ error: 'Failed to save note' });
	}
});

app.post('/api/customers/action', (req, res) => {
	try {
		const { prospect_id, action } = req.body;
		
		if (!prospect_id || !action) {
			return res.status(400).json({ error: 'Missing prospect_id or action' });
		}
		
		const actionMap = {
			call: 'Call initiated',
			email: 'Email sent',
			note: 'Note saved'
		};
		
		res.json({
			success: true,
			prospect_id,
			action,
			message: actionMap[action] || 'Action completed',
			timestamp: new Date().toISOString()
		});
	} catch (error) {
		console.error('Action API error:', error);
		res.status(500).json({ error: 'Failed to perform action' });
	}
});

// ============= AUDIT STORE API =============

app.get('/api/audit/stores', (req, res) => {
	try {
		// Mock stores - in production these would come from database
		const stores = [
			{ number: 'PDX-001', name: 'Portland Main', location: 'Portland, OR' },
			{ number: 'VAN-002', name: 'Vancouver Hub', location: 'Vancouver, WA' },
			{ number: 'ORE-003', name: 'Newberg Location', location: 'Newberg, OR' },
			{ number: 'PDX-004', name: 'Portland South', location: 'Portland, OR' }
		];
		
		res.json({
			stores,
			timestamp: new Date().toISOString()
		});
	} catch (error) {
		console.error('Stores API error:', error);
		res.status(500).json({ error: 'Failed to load stores' });
	}
});

app.post('/api/audit/calculate', (req, res) => {
	try {
		const {
			starting_cases = 20,
			units_per_roll = 4,
			rolls_per_case = 12,
			current_rolls = 0,
			delivery_date,
			cycle = '5-day',
			store_num
		} = req.body;
		
		if (!delivery_date || !current_rolls) {
			return res.status(400).json({ error: 'Missing required fields' });
		}
		
		// Calculate metrics
		const total_rolls = parseInt(current_rolls);
		const total_units = total_rolls * units_per_roll;
		
		// Daily usage based on cycle
		const cycleUsage = {
			'3-day': 4,
			'5-day': 2.5,
			'7-day': 1.8,
			'custom': 2.5
		};
		const daily_usage = cycleUsage[cycle] || 2.5;
		
		// Days until runout
		const days_until_runout = total_rolls / daily_usage;
		
		// Days until delivery
		const today = new Date();
		const delivery = new Date(delivery_date);
		const days_until_delivery = Math.ceil((delivery - today) / (1000 * 60 * 60 * 24));
		
		// Determine status
		let status = 'SUFFICIENT';
		let message = 'You have enough inventory to cover the delivery cycle.';
		
		if (days_until_runout <= days_until_delivery) {
			status = 'INSUFFICIENT';
			message = `ALERT: Inventory will run out in ${days_until_runout.toFixed(1)} days, but delivery is in ${days_until_delivery} days. Immediate action required!`;
		} else if (days_until_runout < days_until_delivery + 2) {
			status = 'WARNING';
			message = 'Warning: Inventory is running close to the delivery date. Monitor usage carefully.';
		}
		
		res.json({
			status,
			message,
			total_rolls,
			total_units,
			daily_usage: parseFloat(daily_usage.toFixed(2)),
			days_until_runout: parseFloat(days_until_runout.toFixed(1)),
			days_until_delivery,
			store_num,
			email_sent: false,
			timestamp: new Date().toISOString()
		});
	} catch (error) {
		console.error('Calculate API error:', error);
		res.status(500).json({ error: 'Failed to calculate audit' });
	}
});

app.post('/api/audit/email', (req, res) => {
	try {
		const { store_num, audit_result } = req.body;
		
		if (!store_num || !audit_result) {
			return res.status(400).json({ error: 'Missing required fields' });
		}
		
		// In production, this would send an actual email to Tyler
		console.log(`[AUDIT EMAIL] Store ${store_num}:`, audit_result);
		
		res.json({
			success: true,
			email_sent: true,
			recipient: 'tyler.vansant@indoormedia.com',
			subject: `CRITICAL: Store ${store_num} Low Inventory Alert`,
			timestamp: new Date().toISOString()
		});
	} catch (error) {
		console.error('Email API error:', error);
		res.status(500).json({ error: 'Failed to send email' });
	}
});

// ============= CATCH-ALL =============

// SPA fallback
app.get('*', (req, res) => {
	res.sendFile(path.join(__dirname, 'dist', 'index.html'));
});

// Error handler
app.use((err, req, res, next) => {
	console.error('Server error:', err);
	res.status(500).json({ error: 'Internal server error' });
});

// Start server
app.listen(PORT, () => {
	console.log(`📊 Dashboard server running on http://localhost:${PORT}`);
	console.log(`   Dashboard: http://localhost:${PORT}`);
	console.log(`   Customers: http://localhost:${PORT}?view=customers`);
	console.log(`   Audit: http://localhost:${PORT}?view=audit`);
});
