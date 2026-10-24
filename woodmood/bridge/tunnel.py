"""Prepare a persistent named-tunnel configuration; no DNS or Cloudflare API writes."""
import json
from pathlib import Path
import re
import uuid

from .config import secure_write


def configure_named_tunnel(config, tunnel_id, hostname, credentials=None):
    tunnel_id = str(uuid.UUID(tunnel_id))
    hostname = hostname.lower().rstrip('.')
    labels = hostname.split('.')
    if (len(labels) < 2 or len(hostname) > 253 or any(
            not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', label) for label in labels)):
        raise ValueError('Use a DNS hostname without a scheme, port or path')
    credentials = Path(credentials or Path.home() / '.cloudflared' / (tunnel_id + '.json')).expanduser().resolve()
    if not credentials.is_file():
        raise ValueError('Named-tunnel credentials file not found; create the tunnel with your own Cloudflare account first')
    content = {
        'tunnel': tunnel_id, 'credentials-file': str(credentials), 'protocol': 'http2',
        'ingress': [{'hostname': hostname, 'service': f'http://127.0.0.1:{config.port}',
                     'originRequest': {'httpHostHeader': 'localhost'}},
                    {'service': 'http_status:404'}],
    }
    path = config.directory / 'tunnel.yml'
    if path.exists():
        try:
            same = json.loads(path.read_text()) == content
        except (ValueError, OSError):
            same = False
        if not same:
            raise ValueError('Existing tunnel.yml was preserved. Review it before changing tunnel settings')
        return path
    # JSON is valid YAML, accepted by cloudflared, and avoids a YAML dependency.
    secure_write(path, json.dumps(content, indent=2))
    return path
