#!/bin/bash
export PATH="/opt/homebrew/bin:$PATH"
cd /Users/tylervansant/.openclaw/workspace
source .venv/bin/activate 2>/dev/null || true
python3 scripts/contract_calendar.py --newer-than 1d >> /tmp/contracts_scan.log 2>&1
