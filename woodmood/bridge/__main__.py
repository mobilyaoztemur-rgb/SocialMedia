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
    owner.add_argument('mode', choices=['begin', 'ready'])
    sub.add_parser('status')
    args = parser.parse_args()
    if args.command == 'init':
        directory = initialize(args.directory)
        print(f'PC bridge initialized. Private state: {directory}')
        print('Access token is in bridge-token inside that directory; its value is not printed.')
        print('Owner mode is active. Start the service, sign in in its Chrome window, then run owner ready.')
        return
    cfg = BridgeConfig.load(args.directory)
    if args.command == 'serve':
        import uvicorn
        from .app import create_app
        # This process must run in the owner's desktop session, not a Windows SYSTEM service.
        uvicorn.run(create_app(cfg), host='127.0.0.1', port=cfg.port,
                    proxy_headers=False, access_log=False, log_level='warning')
    elif args.command == 'status':
        print(json.dumps({'initialized': True, 'owner_paused': cfg.paused_file.exists(),
                          'port': cfg.port, 'profile_present': cfg.profile.exists()}))
    elif args.command == 'owner':
        if args.mode == 'ready':
            cfg.paused_file.unlink(missing_ok=True)
            print('Owner released the browser. Authorized agent requests are now allowed.')
        else:
            cfg.paused_file.touch(mode=0o600, exist_ok=True)
            # Mark paused first so no new browser operations can start. Wait for the active one.
            import httpx
            with httpx.Client(trust_env=False, timeout=3) as client:
                for _ in range(55):
                    try:
                        response = client.get(f'http://127.0.0.1:{cfg.port}/v1/health',
                                              headers={'Authorization': 'Bearer ' + cfg.token})
                        response.raise_for_status()
                        if not response.json()['busy']:
                            print('Browser is idle and reserved for its owner. Agent inspection is paused.')
                            return
                    except httpx.ConnectError:
                        print('Bridge is stopped. Owner mode is saved for the next startup.')
                        return
                    time.sleep(1)
            raise SystemExit('Owner mode is set, but a browser action is still busy; wait before typing.')


if __name__ == '__main__':
    main()
