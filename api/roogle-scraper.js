export default async function handler(req, res) {
  // Set CORS headers
  res.setHeader('Access-Control-Allow-Credentials', 'true');
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,OPTIONS,PATCH,DELETE,POST,PUT');
  res.setHeader('Access-Control-Allow-Headers', 'X-CSRF-Token,X-Requested-With,Accept,Accept-Version,Content-Length,Content-MD5,Content-Type,Date,X-Api-Version');

  if (req.method === 'OPTIONS') {
    res.status(200).end();
    return;
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { storeId, email, password } = req.body;
  
  if (!storeId) {
    return res.status(400).json({ error: 'storeId required' });
  }

  // Note: In production with local server, real credentials are used
  // For now, this returns mock data for demo purposes

  try {
    // For now, return mock data
    // This is a placeholder until we can properly set up browser automation
    const mockData = {
      success: true,
      storeId,
      current: [
        {
          businessName: "Christeen's Cabin",
          status: "Active",
          contractType: "Internet",
          price: "$XX/month",
          category: "Restaurant"
        }
      ],
      past: [
        {
          businessName: "Ferrell Gas",
          status: "Terminated",
          contractType: "Internet",
          price: "$XX/month",
          category: "Gas Station"
        },
        {
          businessName: "Kurts Septic",
          status: "Terminated",
          contractType: "Internet",
          price: "$XX/month",
          category: "Services"
        },
        {
          businessName: "The Bistro",
          status: "Terminated",
          contractType: "Internet",
          price: "$XX/month",
          category: "Restaurant"
        },
        {
          businessName: "Los Agaves",
          status: "Terminated",
          contractType: "Internet",
          price: "$XX/month",
          category: "Restaurant"
        },
        {
          businessName: "News America Marketing",
          status: "Terminated",
          contractType: "Internet",
          price: "$XX/month",
          category: "Marketing"
        },
        {
          businessName: "Peterson Chiropractic",
          status: "Terminated",
          contractType: "Internet",
          price: "$XX/month",
          category: "Healthcare"
        }
      ]
    };

    mockData.all = [...mockData.current, ...mockData.past];

    return res.status(200).json(mockData);

  } catch (error) {
    console.error('Roogle scraper error:', error);
    return res.status(500).json({ error: error.message || 'Scraper failed' });
  }
}
