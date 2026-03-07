#!/bin/bash
cd /Users/tylervansant/.openclaw/workspace
/opt/homebrew/bin/python3 scripts/gmail_contracts_scanner.py >> /tmp/contracts_scan.log 2>&1
