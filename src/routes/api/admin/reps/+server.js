import { json } from '@sveltejs/kit';
import api from '../../../../lib/api.js';

export async function GET() {
	try {
		const overview = await api.getAdminOverview();
		return json(overview.reps);
	} catch (error) {
		console.error('API Error:', error);
		return json({ error: error.message }, { status: 500 });
	}
}
