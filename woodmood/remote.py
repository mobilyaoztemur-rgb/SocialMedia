"""HTTPS control client usable from this Codex environment without registering a new MCP."""
import argparse
import getpass
import json
import mimetypes
import os
from pathlib import Path
from urllib.parse import urlsplit
import uuid

import httpx

from .bridge.config import default_directory, secure_write


def validate_endpoint(url, allow_local=False):
    p = urlsplit(url)
    local = p.hostname in ('127.0.0.1', 'localhost')
    if (p.scheme != 'https' and not (allow_local and local and p.scheme == 'http')) or not p.hostname:
        raise ValueError('Remote bridge must use HTTPS; HTTP is only available for explicit loopback tests')
    if p.username or p.password or p.query or p.fragment or p.path not in ('', '/'):
        raise ValueError('Use only the HTTPS origin, without credentials, path, query or fragment')
    return url.rstrip('/')


class BridgeClient:
    def __init__(self, url, token, cf_id=None, cf_secret=None, allow_local=False, transport=None):
        self.url = validate_endpoint(url, allow_local)
        if not token:
            raise ValueError('A bridge access token is required')
        if bool(cf_id) != bool(cf_secret):
            raise ValueError('Supply both Cloudflare Access service-token fields, or neither')
        headers = {'Authorization': 'Bearer ' + token}
        if cf_id:
            headers.update({'CF-Access-Client-Id': cf_id, 'CF-Access-Client-Secret': cf_secret})
        # Never follow an Access login or other redirect carrying our credentials.
        self.client = httpx.Client(base_url=self.url, headers=headers, follow_redirects=False,
                                   timeout=60, transport=transport)

    def close(self):
        self.client.close()

    def request(self, method, path, body=None, operation_id=None, content=None, content_type=None):
        if not path.startswith('/v1/') or path.startswith('//') or '..' in path or '?' in path or '#' in path:
            raise ValueError('Only /v1/ bridge API paths are accepted')
        headers = {}
        if method.upper() not in ('GET', 'HEAD'):
            headers['Idempotency-Key'] = operation_id or uuid.uuid4().hex
        if content_type:
            headers['Content-Type'] = content_type
        response = self.client.request(method, path, json=body, content=content, headers=headers)
        if 300 <= response.status_code < 400:
            raise RuntimeError('Bridge redirected the request; verify the endpoint and Cloudflare Access authorization')
        if not response.is_success:
            # No raw remote response, request headers, credentials or local proxy URLs in errors.
            detail = None
            try:
                value = response.json().get('detail')
                if isinstance(value, str):
                    detail = value[:500]
            except (ValueError, AttributeError):
                pass
            raise RuntimeError(f'Bridge HTTP {response.status_code}' + (': ' + detail if detail else ''))
        return response

    @classmethod
    def from_settings(cls, path=None):
        path = Path(path or default_directory() / 'remote-client.json')
        stored = json.loads(path.read_text()) if path.exists() else {}
        def setting(env, key):
            return os.environ.get(env) or stored.get(key)
        return cls(setting('WOODMOOD_BRIDGE_URL', 'url') or '',
                   setting('WOODMOOD_BRIDGE_TOKEN', 'token'),
                   setting('CF_ACCESS_CLIENT_ID', 'cf_id'),
                   setting('CF_ACCESS_CLIENT_SECRET', 'cf_secret'))


def main():
    parser = argparse.ArgumentParser(description='Woodmood PC control over HTTPS')
    sub = parser.add_subparsers(dest='command', required=True)
    configure = sub.add_parser('configure')
    configure.add_argument('--url', required=True)
    configure.add_argument('--cloudflare-access', action='store_true')
    sub.add_parser('health')
    sub.add_parser('pages')
    opening = sub.add_parser('open')
    opening.add_argument('url')
    for name in ('snapshot', 'screenshot'):
        cmd = sub.add_parser(name)
        cmd.add_argument('page_id')
        if name == 'screenshot':
            cmd.add_argument('--out', type=Path, required=True)
    request = sub.add_parser('request')
    request.add_argument('method', choices=['GET', 'POST'])
    request.add_argument('path')
    request.add_argument('--body-file', type=Path)
    request.add_argument('--operation-id')
    upload = sub.add_parser('upload')
    upload.add_argument('file', type=Path)
    args = parser.parse_args()
    if args.command == 'configure':
        url = validate_endpoint(args.url)
        stored = {'url': url, 'token': getpass.getpass('PC bridge access token: ')}
        if not stored['token']:
            raise SystemExit('An access token is required')
        if args.cloudflare_access:
            stored['cf_id'] = getpass.getpass('Cloudflare Access Client ID: ')
            stored['cf_secret'] = getpass.getpass('Cloudflare Access Client Secret: ')
        path = default_directory() / 'remote-client.json'
        # A separate temporary file avoids partially overwriting existing credentials.
        temporary = path.with_name('remote-client-' + uuid.uuid4().hex)
        secure_write(temporary, json.dumps(stored))
        temporary.replace(path)
        print('Remote client settings saved outside Git. Credential values are not printed.')
        return
    client = BridgeClient.from_settings()
    try:
        if args.command == 'health':
            response = client.request('GET', '/v1/health')
        elif args.command == 'pages':
            response = client.request('GET', '/v1/pages')
        elif args.command == 'open':
            response = client.request('POST', '/v1/pages', {'url': args.url})
        elif args.command in ('snapshot', 'screenshot'):
            response = client.request('GET', f'/v1/pages/{args.page_id}/{args.command}')
            if args.command == 'screenshot':
                args.out.parent.mkdir(parents=True, exist_ok=True)
                args.out.write_bytes(response.content)
                print('Screenshot saved:', args.out)
                return
        elif args.command == 'upload':
            if args.file.stat().st_size > 25_000_000:
                raise ValueError('Upload exceeds 25 MB')
            response = client.request('POST', '/v1/media', content=args.file.read_bytes(),
                                      content_type=mimetypes.guess_type(args.file.name)[0] or 'application/octet-stream')
        else:
            body = json.loads(args.body_file.read_text()) if args.body_file else None
            response = client.request(args.method, args.path, body, args.operation_id)
        print(json.dumps(response.json(), ensure_ascii=False, indent=2))
    finally:
        client.close()


if __name__ == '__main__':
    try:
        main()
    except (httpx.HTTPError, RuntimeError, ValueError) as exc:
        # HTTP transport errors may contain proxy credentials; only expose their type.
        if isinstance(exc, httpx.HTTPError):
            raise SystemExit('Remote connection failed: ' + type(exc).__name__) from None
        raise SystemExit(str(exc)) from None
