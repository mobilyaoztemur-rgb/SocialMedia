@echo off
setlocal
where cloudflared >nul 2>nul
if errorlevel 1 (
  echo Install cloudflared first: winget install --id Cloudflare.cloudflared --exact
  echo Then open a new terminal and run this script again.
  exit /b 1
)
rem No account, domain, subscription or BrowserAct API key is needed for this trial tunnel.
rem The address changes after restart. Every origin API endpoint still requires its bearer token.
rem Rewrite Host so only loopback Host headers are accepted by the origin server.
cloudflared tunnel --url http://127.0.0.1:8787 --http-host-header localhost --protocol http2
