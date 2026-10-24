#!/usr/bin/env bash
# German Personal Tutor - local mode (Mac / Linux).
# Data is saved in the "data" folder next to this file.
# The app only listens on this computer (localhost).
cd "$(dirname "$0")"

PY=python3
command -v python3 >/dev/null 2>&1 || PY=python

if ! "$PY" -c "import streamlit, openai, gtts" 2>/dev/null; then
    echo "Installing the required packages, this happens only once..."
    "$PY" -m pip install -r requirements.txt
fi

echo
echo "Starting German Personal Tutor... open http://localhost:8501"
echo "Press Ctrl+C to stop the app."
"$PY" -m streamlit run app.py --server.address localhost --server.port 8501
