@echo off
REM German Personal Tutor - local mode (Windows).
REM Data is saved in the "data" folder next to this file.
REM The app only listens on this computer (localhost).
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (set PY=py -3) else (set PY=python)

%PY% -c "import streamlit, openai, gtts" 2>nul
if errorlevel 1 (
    echo Installing the required packages, this happens only once...
    %PY% -m pip install -r requirements.txt
)

echo.
echo Starting German Personal Tutor... your browser opens at http://localhost:8501
echo Close this window to stop the app.
%PY% -m streamlit run app.py --server.address localhost --server.port 8501
pause
