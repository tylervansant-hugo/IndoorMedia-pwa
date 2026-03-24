#!/usr/bin/env python3
"""
Counter Sign Generator API
Calls the same counter_sign_generator.py the bot uses.
"""
from io import BytesIO
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from pathlib import Path
import sys
import logging
import tempfile

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from counter_sign_generator import generate_counter_sign, list_available_store_templates, get_direct_team_by_name

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'}), 200

@app.route('/chains', methods=['GET'])
def get_chains():
    templates = list_available_store_templates()
    return jsonify({'chains': sorted(templates.keys())}), 200

@app.route('/generate', methods=['POST'])
def generate():
    try:
        chain_code = request.form.get('chain_code', '').strip()
        rep_name = request.form.get('rep_name', '').strip()
        landing_page_url = request.form.get('landing_page_url', '').strip() or None

        if not chain_code:
            return jsonify({'error': 'Missing chain_code'}), 400
        if not rep_name:
            return jsonify({'error': 'Missing rep_name'}), 400
        if 'ad_proof' not in request.files:
            return jsonify({'error': 'Missing ad_proof image'}), 400

        # Look up rep info
        team = get_direct_team_by_name(rep_name)
        rep_cell = team.get('cell', '800.247.4793') if team else request.form.get('rep_cell', '800.247.4793')
        rep_email = team.get('email', 'info@indoormedia.com') if team else request.form.get('rep_email', 'info@indoormedia.com')

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)

            # Save ad proof
            ad_path = tmp / 'ad_proof.jpg'
            request.files['ad_proof'].save(str(ad_path))

            # Save business card if provided
            bc_path = None
            if 'business_card' in request.files and request.files['business_card'].filename:
                bc_path = tmp / 'business_card.jpg'
                request.files['business_card'].save(str(bc_path))

            logger.info(f"Generating: chain={chain_code}, rep={rep_name}")

            # Call the SAME function the bot uses
            result = generate_counter_sign(
                chain_code=chain_code,
                ad_image_path=str(ad_path),
                rep_name=rep_name,
                rep_cell=rep_cell,
                rep_email=rep_email,
                landing_page_url=landing_page_url,
                business_card_path=str(bc_path) if bc_path else None,
            )

            # Returns (pdf_bytes, output_path) or (None, None)
            pdf_bytes = result[0]

            if not pdf_bytes:
                return jsonify({'error': 'Generation failed — no PDF produced'}), 500

            logger.info(f"Success: {len(pdf_bytes)} bytes")

            return send_file(
                BytesIO(pdf_bytes),
                mimetype='application/pdf',
                as_attachment=True,
                download_name=f'{chain_code}_CounterSign.pdf',
            )

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = 3333
    print(f"🎨 Counter Sign API on http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
