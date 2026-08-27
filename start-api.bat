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
echo Starting FastAPI at http://127.0.0.1:8010/docs
"%PYTHON%" -m uvicorn app.main:app --host 127.0.0.1 --port 8010

