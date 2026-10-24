import argparse
import json
import time
from pathlib import Path

from .config import BridgeConfig, initialize


def main():
    parser = argparse.ArgumentParser(description='Woodmood persistent PC browser; no BrowserAct account needed')
    parser.add_argument('--directory', type=Path, help='Private state directory outside the Git checkout')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('init')
    sub.add_parser('serve')
    owner = sub.add_parser('owner')
    owner.add_argument('mode', choices=['begin', 'ready', 'browser'])
    sub.add_parser('status')
    tunnel = sub.add_parser('named-tunnel')
    tunnel.add_argument('--id', required=True)
    tunnel.add_argument('--hostname', required=True)
    tunnel.add_argument('--credentials', type=Path)
    args = parser.parse_args()
    if args.command == 'init':
        directory = initialize(args.directory)
        print(f'PC bridge initialized. Private state: {directory}')
        print('Access token is in bridge-token inside that directory; its value is not printed.')
        print('Owner mode is active. Run owner-browser.cmd for manual sign-in, close Chrome, then start-bridge.cmd and agent-ready.cmd.')
        return
    cfg = BridgeConfig.load(args.directory)
    if args.command == 'serve':
        import uvicorn
        from .app import create_app
        # This process must run in the owner's desktop session, not a Windows SYSTEM service.
        uvicorn.run(create_app(cfg), host='127.0.0.1', port=cfg.port,
                    proxy_headers=False, access_log=False, log_level='warning')
    elif args.command == 'named-tunnel':
        from .tunnel import configure_named_tunnel
        path = configure_named_tunnel(cfg, args.id, args.hostname, args.credentials)
        print('Private named-tunnel configuration prepared:', path)
        print('Cloudflare account, active DNS zone and hostname routing must be configured separately.')
    elif args.command == 'status':
        print(json.dumps({'initialized': True, 'owner_paused': cfg.paused_file.exists(),
                          'port': cfg.port, 'profile_present': cfg.profile.exists()}))
    elif args.command == 'owner':
        if args.mode == 'browser':
            # A real manual Chrome window, with neither a driver nor a debugging port.
            # The same profile preserves existing logins; no cookies are copied/exported.
            cfg.paused_file.touch(mode=0o600, exist_ok=True)
            from .local import require_manual_access
            from .native import launch
            require_manual_access(cfg)
            launch(cfg, debugging=False)
            print('Normal Woodmood Chrome opened with no automation connection or debugging port.')
            print('Sign in yourself, close that Chrome window completely, then restart start-bridge.cmd.')
            print('After inspecting your login yourself, run agent-ready.cmd to allow agent access.')
        elif args.mode == 'ready':
            cfg.paused_file.unlink(missing_ok=True)
            print('Owner released the browser. Authorized agent requests are now allowed.')
        else:
            cfg.paused_file.touch(mode=0o600, exist_ok=True)
            # Mark paused first so no new browser operations can start. Wait for the active one.
            import httpx
            from .local import port_available
            if port_available(cfg.port):
                print('Bridge is stopped. Owner mode is saved for the next startup.')
                return
            deadline = time.monotonic() + 50
            with httpx.Client(trust_env=False, timeout=3) as client:
                while time.monotonic() < deadline:
                    try:
                        response = client.get(f'http://127.0.0.1:{cfg.port}/v1/health',
                                              headers={'Authorization': 'Bearer ' + cfg.token})
                        response.raise_for_status()
                        if not response.json()['busy']:
                            print('Browser is idle and reserved for its owner. Agent inspection is paused.')
                            return
                    except httpx.HTTPError:
                        # A timed-out health request does not prove that the browser is idle.
                        raise SystemExit('Owner mode is saved, but the local bridge health check failed. Stop start-bridge.cmd with Ctrl+C before opening manual sign-in.') from None
                    time.sleep(1)
            raise SystemExit('Owner mode is set, but a browser action is still busy; wait before typing.')


if __name__ == '__main__':
    main()
