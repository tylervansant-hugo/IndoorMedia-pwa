import { json } from '@sveltejs/kit';
import api from '../../../../lib/api.js';

export async function GET() {
	try {
		const allocations = await api.getStoreAllocations();
		return json(allocations);
	} catch (error) {
		console.error('API Error:', error);
		return json({ error: error.message }, { status: 500 });
	}
}
