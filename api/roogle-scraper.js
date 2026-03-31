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
  // For now, this returns mock data per store for demo purposes

  try {
    // Get mock data based on store ID
    let mockData = {
      success: true,
      source: 'Mock Data (Demo)',
      storeId,
      current: [],
      past: []
    };

    // QFC Belfair
    if (storeId === 'QFC07X-0101') {
      mockData = {
        success: true,
        source: 'Mock Data (Demo)',
        storeId,
      current: [
        {
          businessName: "Christeen's Cabin",
          status: "Active",
          contractType: "Internet",
          price: "$199/month",
          category: "Restaurant",
          startDate: "2024-06-15",
          endDate: null,
          totalSpent: 1990
        }
      ],
      past: [
        {
          businessName: "Ferrell Gas",
          status: "Terminated",
          contractType: "Internet",
          price: "$149/month",
          category: "Gas Station",
          startDate: "2022-03-10",
          endDate: "2023-09-30",
          totalSpent: 1940
        },
        {
          businessName: "Kurts Septic",
          status: "Terminated",
          contractType: "Internet",
          price: "$179/month",
          category: "Services",
          startDate: "2021-11-01",
          endDate: "2023-04-15",
          totalSpent: 3580
        },
        {
          businessName: "The Bistro",
          status: "Terminated",
          contractType: "Internet",
          price: "$219/month",
          category: "Restaurant",
          startDate: "2023-01-20",
          endDate: "2024-02-28",
          totalSpent: 2409
        },
        {
          businessName: "Los Agaves",
          status: "Terminated",
          contractType: "Internet",
          price: "$189/month",
          category: "Restaurant",
          startDate: "2022-08-05",
          endDate: "2023-11-10",
          totalSpent: 2268
        },
        {
          businessName: "News America Marketing",
          status: "Terminated",
          contractType: "Internet",
          price: "$299/month",
          category: "Marketing",
          startDate: "2020-05-12",
          endDate: "2022-07-20",
          totalSpent: 7776
        },
        {
          businessName: "Peterson Chiropractic",
          status: "Terminated",
          contractType: "Internet",
          price: "$159/month",
          category: "Healthcare",
          startDate: "2023-02-01",
          endDate: "2024-08-31",
          totalSpent: 1908
        }
      ]
      };
    }
    
    // Fred Meyer Tumwater (Trosper Road)
    if (storeId === 'FME07Z-0659') {
      mockData = {
        success: true,
        source: 'Mock Data (Demo)',
        storeId,
        current: [
          {
            businessName: "Starbucks",
            status: "Active",
            contractType: "Internet",
            price: "$249/month",
            category: "Coffee Shop",
            startDate: "2024-01-15",
            endDate: null,
            totalSpent: 2490
          },
          {
            businessName: "Planet Fitness",
            status: "Active",
            contractType: "Internet",
            price: "$199/month",
            category: "Gym",
            startDate: "2023-08-20",
            endDate: null,
            totalSpent: 3980
          }
        ],
        past: [
          {
            businessName: "Subway",
            status: "Terminated",
            contractType: "Internet",
            price: "$149/month",
            category: "Restaurant",
            startDate: "2021-06-10",
            endDate: "2023-03-31",
            totalSpent: 3134
          },
          {
            businessName: "Verizon Wireless",
            status: "Terminated",
            contractType: "Internet",
            price: "$179/month",
            category: "Retail",
            startDate: "2022-02-01",
            endDate: "2024-01-15",
            totalSpent: 3946
          },
          {
            businessName: "Anytime Fitness",
            status: "Terminated",
            contractType: "Internet",
            price: "$159/month",
            category: "Gym",
            startDate: "2022-11-05",
            endDate: "2023-09-30",
            totalSpent: 1908
          },
          {
            businessName: "Chipotle Mexican Grill",
            status: "Terminated",
            contractType: "Internet",
            price: "$189/month",
            category: "Restaurant",
            startDate: "2023-04-12",
            endDate: "2024-05-20",
            totalSpent: 1701
          }
        ]
      };
    }

    // Default: Return current data
    if (!mockData.current.length && !mockData.past.length) {
      mockData.current = [{ businessName: "No data available", status: "N/A", contractType: "N/A", price: "N/A", category: "N/A", startDate: "N/A", endDate: null, totalSpent: 0 }];
    }

    mockData.all = [...mockData.current, ...mockData.past];

    return res.status(200).json(mockData);

  } catch (error) {
    console.error('Roogle scraper error:', error);
    return res.status(500).json({ error: error.message || 'Scraper failed' });
  }
}
