@echo off
setlocal

REM Always run from this script's directory.
cd /d "%~dp0"

set "GAME_URL=https://poki.com/en/g/hill-climb-racing-lite"
set "RUNNER_URL=http://localhost:8080"
set "PYTHON_EXE=.venv\Scripts\python.exe"
set "CAMERA_INDEX=0"
set "CONFIDENCE=0.7"
set "SMOOTH_FRAMES=4"
set "ALLOW_LEFT_HAND=0"

echo ============================================
echo   Gesture Game One-Click Launcher
echo ============================================
echo.

if not exist "%PYTHON_EXE%" (
  echo [ERROR] Virtual environment not found at ".venv\Scripts\python.exe".
  echo         Run setup first:
  echo         python -m venv .venv
  echo         .venv\Scripts\activate
  echo         pip install -r requirements.txt
  echo.
  pause
  exit /b 1
)

echo [1/4] Starting local web runner at %RUNNER_URL% ...
start "Gesture Web Runner Server" /min cmd /c ""%PYTHON_EXE%" -m http.server 8080 --directory web"
timeout /t 1 /nobreak >nul
start "" "%RUNNER_URL%"
timeout /t 2 /nobreak >nul

echo [2/4] Running gesture controller self-check...
"%PYTHON_EXE%" main.py --self-check --camera-index %CAMERA_INDEX%
if errorlevel 1 (
  echo.
  echo [ERROR] Self-check failed. Fix the reported issue, then try again.
  echo.
  pause
  exit /b 1
)

echo [3/4] Starting gesture controller in no-window mode...
echo       This keeps browser focus stable for key sync.
echo       Stop with Ctrl+C in this terminal.
echo.

if "%ALLOW_LEFT_HAND%"=="1" (
  "%PYTHON_EXE%" main.py --camera-index %CAMERA_INDEX% --confidence %CONFIDENCE% --smooth-frames %SMOOTH_FRAMES% --allow-left-hand --no-window
) else (
  "%PYTHON_EXE%" main.py --camera-index %CAMERA_INDEX% --confidence %CONFIDENCE% --smooth-frames %SMOOTH_FRAMES% --no-window
)

echo.
echo [4/4] Gesture controller exited.
pause
exit /b 0
