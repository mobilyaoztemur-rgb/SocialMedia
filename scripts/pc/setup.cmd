@echo off
setlocal
cd /d "%~dp0..\.."
where uv >nul 2>nul
if errorlevel 1 (
  echo Install uv first in a terminal: winget install --id astral-sh.uv --exact
  echo Then open a new terminal and run this script again.
  exit /b 1
)
uv sync --frozen --extra browser
if errorlevel 1 exit /b 1
uv run --frozen --extra browser python -m woodmood.bridge init
if errorlevel 1 exit /b 1
echo Setup finished. Install Google Chrome if it is not already installed.
echo Run owner-browser.cmd FIRST, sign in in normal Chrome, then close that window.
echo Next run start-bridge.cmd and agent-ready.cmd.
