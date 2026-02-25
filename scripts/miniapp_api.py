#!/usr/bin/env python3
"""
IndoorMedia Mini App API
Serves prospect data + pricing to Telegram mini app
"""

import json
import os
import sys
from pathlib import Path
from flask import Flask, jsonify, request
from flask_cors import CORS
import logging
from flask import send_file

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

WORKSPACE = Path(__file__).parent.parent
DATA_DIR = WORKSPACE / "data" / "store-rates"
STORES_FILE = DATA_DIR / "stores.json"

app = Flask(__name__)
CORS(app)

# Load stores
with open(STORES_FILE) as f:
    STORES_LIST = json.load(f)
STORES = {s["StoreName"]: s for s in STORES_LIST}

# Import tools
sys.path.insert(0, str(WORKSPACE / "scripts"))
from prospecting_tool_enhanced import ProspectingToolEnhanced

def calculate_pricing_plans(store, ad_type='single'):
    """Calculate pricing with payment plans."""
    base = store.get('DoubleAd' if ad_type == 'double' else 'SingleAd', 0)
    PROD = 125.0
    
    return {
        'plans': {
            'monthly': {
                'per_installment': round((base + PROD) / 12, 2),
                'total': round(base + PROD, 2),
                'display': f"${round((base + PROD) / 12, 2):.2f}/mo × 12 = ${round(base + PROD, 2):.2f}"
            },
            '3month': {
                'per_installment': round(((base * 0.90) + PROD) / 3, 2),
                'total': round((base * 0.90) + PROD, 2),
                'display': f"${round(((base * 0.90) + PROD) / 3, 2):.2f} × 3 = ${round((base * 0.90) + PROD, 2):.2f} (10% off)"
            },
            '6month': {
                'per_installment': round(((base * 0.925) + PROD) / 6, 2),
                'total': round((base * 0.925) + PROD, 2),
                'display': f"${round(((base * 0.925) + PROD) / 6, 2):.2f} × 6 = ${round((base * 0.925) + PROD, 2):.2f} (7.5% off)"
            },
            'paid_full': {
                'total': round((base * 0.85) + PROD, 2),
                'display': f"${round((base * 0.85) + PROD, 2):.2f} (one payment, 15% off)"
            }
        }
    }

prospecting_tool = None


def get_prospecting_tool():
    """Lazy load prospecting tool."""
    global prospecting_tool
    if not prospecting_tool:
        prospecting_tool = ProspectingToolEnhanced()
    return prospecting_tool


@app.route('/', methods=['GET'])
@app.route('/miniapp', methods=['GET'])
def miniapp():
    """Serve the mini app HTML."""
    miniapp_file = WORKSPACE / "scripts" / "miniapp.html"
    if miniapp_file.exists():
        with open(miniapp_file) as f:
            return f.read(), 200, {'Content-Type': 'text/html; charset=utf-8'}
    return jsonify({'error': 'Mini app not found'}), 404


@app.route('/health', methods=['GET'])
def health():
    """Health check."""
    return jsonify({'status': 'ok'})


@app.route('/api/store/<store_num>', methods=['GET'])
def get_store(store_num):
    """Get store details."""
    store_num = store_num.upper()
    store = STORES.get(store_num)
    
    if not store:
        return jsonify({'error': 'Store not found'}), 404
    
    return jsonify({
        'store_number': store['StoreName'],
        'chain': store['GroceryChain'],
        'city': store['City'],
        'state': store['State'],
        'address': store['Address'],
        'single_ad': store['SingleAd'],
        'double_ad': store['DoubleAd'],
    })


@app.route('/api/prospects/<store_num>', methods=['GET'])
def get_prospects(store_num):
    """Get top prospects for a store."""
    store_num = store_num.upper()
    limit = request.args.get('limit', 10, type=int)
    
    # Check store exists
    store = STORES.get(store_num)
    if not store:
        return jsonify({'error': 'Store not found'}), 404
    
    try:
        tool = get_prospecting_tool()
        prospects = tool.run_prospecting(store_num, limit)
        
        # Format for UI
        formatted = []
        for p in prospects:
            formatted.append({
                'name': p['name'],
                'likelihood_score': p['likelihood_score'],
                'address': p['address'],
                'phone': p['phone'],
                'distance_miles': p.get('distance_miles', 0),
                'rating': p.get('rating', 0),
                'reviews': p.get('user_ratings_total', 0),
                'advertising': p.get('advertising_signal', {}).get('found_advertising', False),
                'emoji': '🔥' if p['likelihood_score'] >= 80 else '⭐' if p['likelihood_score'] >= 70 else '👀'
            })
        
        return jsonify({'prospects': formatted})
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/pricing/<store_num>', methods=['GET'])
def get_pricing(store_num):
    """Get pricing for a store."""
    store_num = store_num.upper()
    ad_type = request.args.get('ad_type', 'single')
    
    store = STORES.get(store_num)
    if not store:
        return jsonify({'error': 'Store not found'}), 404
    
    try:
        base = store.get('DoubleAd' if ad_type == 'double' else 'SingleAd', 0)
        pricing_data = calculate_pricing_plans(store, ad_type)
        
        return jsonify({
            'store': store_num,
            'chain': store['GroceryChain'],
            'city': store['City'],
            'base_price': base,
            'ad_type': ad_type,
            'plans': pricing_data['plans']
        })
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/cities', methods=['GET'])
def get_cities():
    """Get all cities."""
    cities = sorted(set(s['City'] for s in STORES_LIST))
    return jsonify({'cities': cities})


@app.route('/api/chains', methods=['GET'])
def get_chains():
    """Get all chains."""
    chains = sorted(set(s['GroceryChain'] for s in STORES_LIST))
    return jsonify({'chains': chains})


if __name__ == '__main__':
    logger.info("🚀 IndoorMedia Mini App API starting on :5000")
    app.run(debug=False, host='0.0.0.0', port=5000)
