import { json } from '@sveltejs/kit';
import api from '../../../lib/api.js';

export async function GET() {
	try {
		const testimonials = await api.getTestimonials();
		return json(testimonials);
	} catch (error) {
		console.error('API Error:', error);
		return json({ error: error.message }, { status: 500 });
	}
}
