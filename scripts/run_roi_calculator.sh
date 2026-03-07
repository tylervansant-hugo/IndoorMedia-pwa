#!/bin/bash
# Launch ROI Calculator Streamlit App

WORKSPACE="/Users/tylervansant/.openclaw/workspace"
cd "$WORKSPACE"

# Activate venv
source .venv_roi/bin/activate

# Run Streamlit
streamlit run scripts/roi_calculator.py --server.port=8501 --logger.level=error
