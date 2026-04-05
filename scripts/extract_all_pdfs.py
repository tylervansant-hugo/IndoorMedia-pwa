#!/usr/bin/env python3
"""Extract text from all 8 Zone 7 renewal PDFs using pymupdf and save raw text for analysis."""
import fitz
import os

PDFS = {
    'C1': '/Users/tylervansant/.openclaw/media/inbound/ZONE_7_C1_2026---245df008-f83b-4ea9-a617-b8190cb84a72.pdf',
    'C4': '/Users/tylervansant/.openclaw/media/inbound/ZONE_7_C4_2025---037ca158-1a5e-48d0-9c20-a560083a8643.pdf',
    'B1': '/Users/tylervansant/.openclaw/media/inbound/ZONE_7_B1_2026---ae4e374e-0f97-49e3-b98d-0c61d75b2a22.pdf',
    'A2': '/Users/tylervansant/.openclaw/media/inbound/Zone_7_A2_2026---d24f9693-aa8b-414a-8def-957cfda9684e.pdf',
    'C2': '/Users/tylervansant/.openclaw/media/inbound/ZONE_7_C2_2026---a6ecf32b-2ab8-4edf-b758-e453579fa236.pdf',
    'B4': '/Users/tylervansant/.openclaw/media/inbound/ZONE_7_B4_2025---bb3bdc2c-366c-49eb-9b1a-bfa9a4c2354f.pdf',
    'A1': '/Users/tylervansant/.openclaw/media/inbound/ZONE_7_A1_2026---e8e16115-0a02-4b62-852b-ff203a940d8e.pdf',
    'A4': '/Users/tylervansant/.openclaw/media/inbound/ZONE_7_A4_2025---18a28afd-7409-4718-9409-705e1b52638c.pdf',
}

outdir = '/Users/tylervansant/.openclaw/workspace/scripts/pdf_text'
os.makedirs(outdir, exist_ok=True)

for cycle, path in PDFS.items():
    doc = fitz.open(path)
    with open(f'{outdir}/{cycle}.txt', 'w') as f:
        for page in doc:
            # Extract with "blocks" method for better structure
            blocks = page.get_text("blocks")
            for b in blocks:
                text = b[4].strip()
                if text:
                    f.write(text + '\n')
            f.write('\n=== PAGE BREAK ===\n\n')
    doc.close()
    # Count lines
    with open(f'{outdir}/{cycle}.txt') as f:
        lines = f.readlines()
        zone_lines = [l for l in lines if l.strip().startswith('07')]
        print(f'{cycle}: {len(lines)} total lines, {len(zone_lines)} zone lines')
