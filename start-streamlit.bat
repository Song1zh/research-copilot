@echo off
chcp 65001 >nul
setlocal

set "ROOT=%~dp0"
set "PYTHON=%ROOT%.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
  echo Python virtual environment not found:
  echo %PYTHON%
  pause
  exit /b 1
)

cd /d "%ROOT%"
set "USERPROFILE=%ROOT%.streamlit-home"
echo Starting Streamlit demo at http://127.0.0.1:8501
"%PYTHON%" -m streamlit run demo\streamlit_app.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false
