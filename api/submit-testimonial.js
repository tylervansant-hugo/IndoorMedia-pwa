// Vercel Serverless Function: Submit Testimonial via Email
// Sends formatted testimonial to Tyler + testimonials@rtui.com

export default async function handler(req, res) {
  // CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const RESEND_API_KEY = process.env.RESEND_API_KEY;
  if (!RESEND_API_KEY) {
    return res.status(500).json({ error: 'Email service not configured' });
  }

  try {
    const t = req.body;

    const subject = `📋 New Testimonial: ${t.business || 'Unknown Business'} — ${t.groceryChain || ''} ${t.storeNumber || ''}`.trim();

    const html = `
      <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #CC0000; border-bottom: 2px solid #CC0000; padding-bottom: 8px;">
          📋 New Testimonial Submitted
        </h2>
        
        <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
          <tr><td style="padding: 8px; font-weight: bold; width: 40%; border-bottom: 1px solid #eee;">Contact Name</td><td style="padding: 8px; border-bottom: 1px solid #eee;">${t.name || '—'}</td></tr>
          <tr><td style="padding: 8px; font-weight: bold; border-bottom: 1px solid #eee;">Business Name</td><td style="padding: 8px; border-bottom: 1px solid #eee;">${t.business || '—'}</td></tr>
          <tr><td style="padding: 8px; font-weight: bold; border-bottom: 1px solid #eee;">Address</td><td style="padding: 8px; border-bottom: 1px solid #eee;">${t.address || '—'}</td></tr>
          <tr><td style="padding: 8px; font-weight: bold; border-bottom: 1px solid #eee;">Phone</td><td style="padding: 8px; border-bottom: 1px solid #eee;">${t.phone || '—'}</td></tr>
          <tr><td style="padding: 8px; font-weight: bold; border-bottom: 1px solid #eee;">Grocery Chain</td><td style="padding: 8px; border-bottom: 1px solid #eee;">${t.groceryChain || '—'}</td></tr>
          <tr><td style="padding: 8px; font-weight: bold; border-bottom: 1px solid #eee;">Zone</td><td style="padding: 8px; border-bottom: 1px solid #eee;">${t.zone || '—'}</td></tr>
          <tr><td style="padding: 8px; font-weight: bold; border-bottom: 1px solid #eee;">Store Number</td><td style="padding: 8px; border-bottom: 1px solid #eee;">${t.storeNumber || '—'}</td></tr>
          <tr><td style="padding: 8px; font-weight: bold; border-bottom: 1px solid #eee;">Coupons / Week</td><td style="padding: 8px; border-bottom: 1px solid #eee;">${t.couponsPerWeek || '—'}</td></tr>
          <tr><td style="padding: 8px; font-weight: bold; border-bottom: 1px solid #eee;">Avg Ticket Price</td><td style="padding: 8px; border-bottom: 1px solid #eee;">${t.avgTicket ? '$' + t.avgTicket : '—'}</td></tr>
          <tr><td style="padding: 8px; font-weight: bold; border-bottom: 1px solid #eee;">ROI Rating</td><td style="padding: 8px; border-bottom: 1px solid #eee;">${t.roi || '—'}</td></tr>
          <tr><td style="padding: 8px; font-weight: bold; border-bottom: 1px solid #eee;">How Long Advertised</td><td style="padding: 8px; border-bottom: 1px solid #eee;">${t.duration || '—'}</td></tr>
          <tr><td style="padding: 8px; font-weight: bold; border-bottom: 1px solid #eee;">Would Renew?</td><td style="padding: 8px; border-bottom: 1px solid #eee;">${t.wouldRenew || '—'}</td></tr>
          <tr><td style="padding: 8px; font-weight: bold; border-bottom: 1px solid #eee;">Would Recommend?</td><td style="padding: 8px; border-bottom: 1px solid #eee;">${t.recommend || '—'}</td></tr>
        </table>

        ${t.comments ? `
        <div style="background: #f8f8f8; border-left: 4px solid #CC0000; padding: 12px 16px; margin: 16px 0;">
          <strong>Comments:</strong><br/>
          ${t.comments}
        </div>
        ` : ''}

        ${t.couponImage ? `<p style="color: #666;">📎 Coupon image attached: ${t.couponImage}</p>` : ''}

        <p style="color: #999; font-size: 12px; margin-top: 24px; border-top: 1px solid #eee; padding-top: 12px;">
          Submitted by <strong>${t.submittedBy || 'Unknown Rep'}</strong> on ${new Date().toLocaleString('en-US', { timeZone: 'America/Los_Angeles' })} PT<br/>
          via imPro Sales Portal
        </p>
      </div>
    `;

    // Send to both recipients
    const response = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${RESEND_API_KEY}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        from: 'imPro Portal <noreply@updates.indoormedia.com>',
        to: ['tyler.vansant@indoormedia.com', 'testimonials@rtui.com'],
        subject,
        html,
      }),
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      console.error('Resend error:', errData);
      return res.status(500).json({ error: 'Failed to send email', details: errData });
    }

    const result = await response.json();
    return res.status(200).json({ success: true, emailId: result.id });

  } catch (err) {
    console.error('Submit testimonial error:', err);
    return res.status(500).json({ error: 'Internal server error' });
  }
}
