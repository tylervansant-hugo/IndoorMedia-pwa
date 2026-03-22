// Google Places API wrapper
const API_KEY = 'AIzaSyBoslNJj8aO6wkQOfkH9e4qTVJZ-G9nOuA';
const NOMINATIM_URL = 'https://nominatim.openstreetmap.org';

/**
 * Search for nearby places using Google Places API
 * Falls back to Nominatim if Google fails (offline support)
 */
export async function searchNearbyPlaces(lat, lng, keyword, types = []) {
  try {
    // Try Google Places API first
    return await searchGooglePlaces(lat, lng, keyword, types);
  } catch (error) {
    console.warn('Google Places API failed, falling back to Nominatim:', error);
    // Fall back to Nominatim
    return await searchNominatim(lat, lng, keyword);
  }
}

/**
 * Search using Google Places API (Text Search)
 */
async function searchGooglePlaces(lat, lng, keyword, types = []) {
  const radius = 8000; // 8km radius
  
  // Build search query
  let query = keyword;
  if (types.length > 0) {
    query += ` ${types[0]}`;
  }

  const params = new URLSearchParams({
    location: `${lat},${lng}`,
    radius: radius.toString(),
    key: API_KEY,
    query: query,
    fields: 'places.place_id,places.name,places.formatted_address,places.opening_hours,places.rating,places.user_ratings_total,places.photos,places.types,places.permanently_closed'
  });

  const response = await fetch(
    `https://places.googleapis.com/v1/places:searchNearby?key=${API_KEY}`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Goog-FieldMask': 'places.place_id,places.name,places.formatted_address,places.opening_hours,places.rating,places.user_ratings_total,places.photos,places.types,places.business_status'
      },
      body: JSON.stringify({
        location: {
          latitude: lat,
          longitude: lng
        },
        radius: radius,
        textQuery: query
      })
    }
  );

  if (!response.ok) {
    // Fall back to older endpoint
    return await searchGooglePlacesLegacy(lat, lng, keyword, types);
  }

  const data = await response.json();
  return (data.places || []).map(place => normalizeGooglePlace(place));
}

/**
 * Legacy Google Places Web Service (Text Search)
 */
async function searchGooglePlacesLegacy(lat, lng, keyword, types = []) {
  const radius = 8000;
  
  let query = keyword;
  if (types.length > 0 && !keyword.includes(types[0])) {
    query = `${keyword} ${types[0]}`;
  }

  const params = new URLSearchParams({
    location: `${lat},${lng}`,
    radius: radius.toString(),
    query: query,
    key: API_KEY
  });

  const response = await fetch(
    `https://maps.googleapis.com/maps/api/place/textsearch/json?${params}`
  );

  if (!response.ok) {
    throw new Error(`Google Places API error: ${response.status}`);
  }

  const data = await response.json();
  
  if (data.status !== 'OK' && data.status !== 'ZERO_RESULTS') {
    throw new Error(`Google Places status: ${data.status}`);
  }

  return (data.results || [])
    .filter(place => place.business_status !== 'CLOSED_PERMANENTLY')
    .map(place => normalizeGooglePlace(place));
}

/**
 * Get detailed information about a place (for expandable cards)
 */
export async function getPlaceDetails(placeId) {
  try {
    const response = await fetch(
      `https://maps.googleapis.com/maps/api/place/details/json?place_id=${placeId}&fields=name,formatted_address,formatted_phone_number,opening_hours,website,business_status,photos,rating,user_ratings_total,types,url,place_id&key=${API_KEY}`
    );

    if (!response.ok) {
      throw new Error(`Place details API error: ${response.status}`);
    }

    const data = await response.json();
    
    if (data.status !== 'OK') {
      throw new Error(`Place details status: ${data.status}`);
    }

    return normalizeGooglePlace(data.result);
  } catch (error) {
    console.error('Failed to get place details:', error);
    return null;
  }
}

/**
 * Get photo URL for a place
 */
export function getPhotoUrl(photoReference, maxWidth = 400) {
  return `https://maps.googleapis.com/maps/api/place/photo?maxwidth=${maxWidth}&photoreference=${photoReference}&key=${API_KEY}`;
}

/**
 * Normalize Google Place data to our schema
 */
function normalizeGooglePlace(place) {
  const isOpen = place.opening_hours?.open_now;
  const hours = place.opening_hours?.weekday_text || [];
  
  return {
    placeId: place.place_id,
    name: place.name,
    address: place.formatted_address || place.vicinity || '',
    phone: place.formatted_phone_number || '',
    website: place.website || '',
    rating: place.rating || 0,
    reviewCount: place.user_ratings_total || 0,
    isOpen: isOpen,
    hours: hours,
    photos: (place.photos || []).slice(0, 3),
    types: place.types || [],
    mapsUrl: place.url || `https://maps.google.com/?q=${encodeURIComponent(place.name)}`,
    businessStatus: place.business_status || 'OPERATIONAL'
  };
}

/**
 * Fallback: Search using Nominatim (OpenStreetMap)
 */
async function searchNominatim(lat, lng, keyword) {
  const response = await fetch(
    `${NOMINATIM_URL}/search.php?q=${encodeURIComponent(keyword)}&format=json&lat=${lat}&lon=${lng}&limit=10`
  );

  if (!response.ok) {
    throw new Error(`Nominatim API error: ${response.status}`);
  }

  const data = await response.json();
  
  return data.map(place => ({
    placeId: place.osm_id.toString(),
    name: place.name,
    address: place.display_name,
    phone: '',
    website: '',
    rating: 0,
    reviewCount: 0,
    isOpen: null,
    hours: [],
    photos: [],
    types: [],
    mapsUrl: `https://www.openstreetmap.org/${place.osm_type}/${place.osm_id}`,
    businessStatus: 'OPERATIONAL',
    source: 'nominatim'
  }));
}

/**
 * Geocode an address to coordinates
 */
export async function geocodeAddress(address) {
  try {
    const response = await fetch(
      `https://maps.googleapis.com/maps/api/geocode/json?address=${encodeURIComponent(address)}&key=${API_KEY}`
    );

    if (!response.ok) {
      throw new Error(`Geocode API error: ${response.status}`);
    }

    const data = await response.json();
    
    if (data.status !== 'OK' || data.results.length === 0) {
      throw new Error(`Geocode status: ${data.status}`);
    }

    const location = data.results[0].geometry.location;
    return {
      lat: location.lat,
      lng: location.lng,
      address: data.results[0].formatted_address
    };
  } catch (error) {
    console.error('Geocoding failed:', error);
    return null;
  }
}

/**
 * Calculate likelihood score based on business signals
 */
export function calculateLikelihoodScore(place) {
  let score = 50; // Base score

  // Rating (0-20 points)
  if (place.rating) {
    score += (place.rating / 5) * 20;
  }

  // Review count (0-15 points) - established business
  if (place.reviewCount) {
    score += Math.min((place.reviewCount / 100) * 15, 15);
  }

  // Open now (10 points)
  if (place.isOpen === true) {
    score += 10;
  }

  // Has website (5 points)
  if (place.website) {
    score += 5;
  }

  return Math.min(Math.round(score), 100);
}

/**
 * Get "Open Now" status with formatted hours
 */
export function getOpenNowStatus(place) {
  if (place.isOpen === null || place.isOpen === undefined) {
    return { status: 'unknown', badge: '⏰', text: 'Hours unavailable' };
  }

  if (place.isOpen) {
    return { status: 'open', badge: '✅', text: 'Open Now' };
  } else {
    return { status: 'closed', badge: '❌', text: 'Closed' };
  }
}
