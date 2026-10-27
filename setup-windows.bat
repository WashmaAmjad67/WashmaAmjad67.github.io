@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Install Python 3.11 or newer from python.org, then run this again.
  pause
  exit /b 1
)
py -3 -m venv .venv
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m pip install -r requirements.txt faster-whisper
if errorlevel 1 goto failed
if not exist .env copy .env.example .env >nul
where ollama >nul 2>nul
if errorlevel 1 (
  echo Install Ollama from https://ollama.com/download/windows then run this setup again.
  pause
  exit /b 1
)
echo Downloading the default local model. This needs approximately 1 GB disk space.
ollama pull qwen2.5:1.5b
if errorlevel 1 goto failed
echo Setup complete. Double-click start-windows.bat to open Atlas.
pause
exit /b 0
:failed
echo Setup failed. Review the error above, then try again.
pause
exit /b 1
