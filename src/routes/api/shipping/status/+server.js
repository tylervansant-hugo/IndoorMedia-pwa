import { json } from '@sveltejs/kit';
import api from '../../../../lib/api.js';

export async function GET() {
	try {
		const shippingStatus = await api.getFormattedShippingStatus();
		return json(shippingStatus);
	} catch (error) {
		console.error('API Error:', error);
		return json({ error: error.message }, { status: 500 });
	}
}
