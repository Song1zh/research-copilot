@echo off
chcp 65001 >nul
setlocal

set "ROOT=%~dp0"

start "Research Copilot API" cmd /k ""%ROOT%start-api.bat""
start "Research Copilot Streamlit" cmd /k ""%ROOT%start-streamlit.bat""

echo FastAPI docs:    http://127.0.0.1:8010/docs
echo Streamlit demo:  http://127.0.0.1:8501

