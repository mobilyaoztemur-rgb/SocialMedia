@echo off
setlocal
where cloudflared >nul 2>nul
if errorlevel 1 (
  echo Install cloudflared first: winget install --id Cloudflare.cloudflared --exact
  exit /b 1
)
if not exist "%LOCALAPPDATA%\WoodmoodSocial\tunnel.yml" (
  echo Named tunnel is not configured yet. Follow docs\STABLE_ADDRESS.md with the agent.
  echo Do not paste tunnel credentials into the repository.
  exit /b 1
)
cloudflared tunnel --config "%LOCALAPPDATA%\WoodmoodSocial\tunnel.yml" run
