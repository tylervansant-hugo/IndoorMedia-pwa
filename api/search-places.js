const API_KEY = process.env.GOOGLE_PLACES_API_KEY || 'AIzaSyBoslNJj8aO6wkQOfkH9e4qTVJZ-G9nOuA';

export default async (req, res) => {
  // Allow CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { lat, lng, keyword } = req.body;

  if (!lat || !lng || !keyword) {
    return res.status(400).json({ error: 'Missing required parameters' });
  }

  try {
    // Use Text Search (New) — supports textQuery + location bias
    const response = await fetch('https://places.googleapis.com/v1/places:searchText', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Goog-Api-Key': API_KEY,
        'X-Goog-FieldMask': 'places.displayName,places.formattedAddress,places.rating,places.userRatingCount,places.location,places.businessStatus,places.nationalPhoneNumber,places.websiteUri,places.googleMapsUri'
      },
      body: JSON.stringify({
        textQuery: keyword,
        locationBias: {
          circle: {
            center: { latitude: lat, longitude: lng },
            radius: 8000.0
          }
        },
        maxResultCount: 10
      })
    });

    if (!response.ok) {
      const errText = await response.text();
      console.error('Google API error:', response.status, errText);
      throw new Error(`Google API error: ${response.status}`);
    }

    const data = await response.json();

    const R = 3959; // Earth radius miles
    function haversine(lat1, lon1, lat2, lon2) {
      const dLat = (lat2 - lat1) * Math.PI / 180;
      const dLon = (lon2 - lon1) * Math.PI / 180;
      const a = Math.sin(dLat / 2) ** 2 +
        Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
        Math.sin(dLon / 2) ** 2;
      return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    }

    const places = (data.places || []).map((place) => {
      const pLat = place.location?.latitude || 0;
      const pLng = place.location?.longitude || 0;
      const dist = haversine(lat, lng, pLat, pLng);
      const rating = place.rating || 0;
      const reviews = place.userRatingCount || 0;

      // Score: distance (40), rating (30), reviews (30)
      const distScore = Math.max(0, 40 - (dist * 8));
      const ratingScore = (rating / 5) * 30;
      const reviewScore = Math.min(30, (reviews / 100) * 30);
      const score = Math.round(distScore + ratingScore + reviewScore);

      return {
        id: place.displayName?.text || 'unknown',
        name: place.displayName?.text || 'Unnamed',
        address: place.formattedAddress || 'Address unavailable',
        rating: rating,
        reviews: reviews,
        distance: Math.round(dist * 10) / 10,
        score: Math.min(100, score),
        phone: place.nationalPhoneNumber || null,
        website: place.websiteUri || null,
        mapsUrl: place.googleMapsUri || null,
        status: place.businessStatus === 'OPERATIONAL' ? 'open' : 'check',
        lat: pLat,
        lng: pLng
      };
    }).sort((a, b) => b.score - a.score);

    res.status(200).json({ success: true, places });
  } catch (error) {
    console.error('Google Places error:', error);
    res.status(500).json({ error: 'Failed to search places', details: error.message });
  }
};
