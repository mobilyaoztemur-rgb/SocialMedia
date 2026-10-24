"""Launch a real, dedicated Chrome; sign-in never requires an automation connection."""
import asyncio
import subprocess
import time
from urllib.parse import urlsplit

import httpx


def chrome_arguments(config, *, debugging=False):
    if not config.executable:
        raise ValueError('Google Chrome executable not found; install Chrome or set executable in bridge.json')
    args = [config.executable, '--user-data-dir=' + str(config.profile),
            '--no-first-run', '--no-default-browser-check', '--disable-background-mode']
    if debugging:
        # Only loopback debugging on the separate Woodmood profile; no public CDP listener.
        args.extend(['--remote-debugging-address=127.0.0.1', '--remote-debugging-port=0'])
    if config.headless:
        args.extend(['--headless=new', '--disable-dev-shm-usage'])
    if not config.sandbox:
        args.append('--no-sandbox')
    args.append('about:blank')
    return args


def launch(config, *, debugging=False):
    config.profile.mkdir(mode=0o700, parents=True, exist_ok=True)
    flags = 0
    import sys
    if sys.platform == 'win32':
        flags = subprocess.CREATE_NEW_PROCESS_GROUP
        if not debugging:
            flags |= subprocess.DETACHED_PROCESS
    return subprocess.Popen(chrome_arguments(config, debugging=debugging),
                            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, creationflags=flags)


def verified_endpoint(config):
    """Read Chrome's private profile endpoint marker, checking its exact websocket ID."""
    try:
        lines = (config.profile / 'DevToolsActivePort').read_text().splitlines()
        port = int(lines[0])
        path = lines[1]
        if not 1024 <= port <= 65535 or not path.startswith('/devtools/browser/'):
            return None
        with httpx.Client(trust_env=False, timeout=0.8) as client:
            r = client.get(f'http://127.0.0.1:{port}/json/version')
            r.raise_for_status()
            data = r.json()
        websocket = urlsplit(data['webSocketDebuggerUrl'])
        if (websocket.scheme != 'ws' or websocket.hostname not in ('127.0.0.1', 'localhost', '::1')
                or websocket.port != port or websocket.path != path):
            return None
        return f'http://127.0.0.1:{port}'
    except (OSError, ValueError, KeyError, IndexError, httpx.HTTPError):
        return None


async def start_debug_browser(config):
    endpoint = await asyncio.to_thread(verified_endpoint, config)
    if endpoint:
        return endpoint, None
    # Do not delete an old marker or reuse an arbitrary port. Readiness checks its websocket ID.
    process = launch(config, debugging=True)
    deadline = time.monotonic() + 35
    while time.monotonic() < deadline:
        endpoint = await asyncio.to_thread(verified_endpoint, config)
        if endpoint:
            return endpoint, process
        if process.poll() is not None:
            raise ValueError('Chrome did not open its control connection. Close the separate Woodmood Chrome window and restart start-bridge.cmd.')
        await asyncio.sleep(0.2)
    process.terminate()
    try:
        await asyncio.to_thread(process.wait, 5)
    except subprocess.TimeoutExpired:
        process.kill()
        await asyncio.to_thread(process.wait, 5)
    raise ValueError('Chrome control startup timed out. Close the Woodmood browser and check executable in bridge.json.')
