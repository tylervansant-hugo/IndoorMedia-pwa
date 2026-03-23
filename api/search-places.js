const API_KEY = process.env.GOOGLE_PLACES_API_KEY || 'AIzaSyBoslNJj8aO6wkQOfkH9e4qTVJZ-G9nOuA';

export default async (req, res) => {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { lat, lng, keyword } = req.body;

  if (!lat || !lng || !keyword) {
    return res.status(400).json({ error: 'Missing required parameters' });
  }

  try {
    const response = await fetch('https://places.googleapis.com/v1/places:searchNearby', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Goog-FieldMask': 'places.name,places.formattedAddress,places.rating,places.userRatingCount,places.location,places.displayName,places.businessStatus,places.openingHours'
      },
      body: JSON.stringify({
        location: { latitude: lat, longitude: lng },
        radiusMeters: 8000,
        textQuery: keyword
      })
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    const data = await response.json();
    
    // Format results
    const places = (data.places || []).slice(0, 10).map((place) => {
      const distance = Math.sqrt(
        Math.pow(place.location.latitude - lat, 2) +
        Math.pow(place.location.longitude - lng, 2)
      ) * 69; // rough miles conversion
      
      return {
        id: place.name,
        name: place.displayName?.text || place.name || 'Unnamed',
        address: place.formattedAddress || 'Address unavailable',
        rating: place.rating || 0,
        reviews: place.userRatingCount || 0,
        distance: distance,
        score: Math.min(100, Math.round((place.rating || 0) * 15 + (Math.min(place.userRatingCount || 0, 100) / 100) * 20 + 50)),
        status: place.openingHours?.openNow ? 'open' : 'check',
        lat: place.location.latitude,
        lng: place.location.longitude
      };
    });

    res.status(200).json({ success: true, places });
  } catch (error) {
    console.error('Google Places error:', error);
    res.status(500).json({ error: 'Failed to search places', details: error.message });
  }
};
