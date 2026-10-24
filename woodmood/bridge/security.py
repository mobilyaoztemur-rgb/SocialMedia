import hashlib
import hmac
import json
from urllib.parse import urlsplit, urlunsplit

# Navigation only; site resources and their legitimate CDNs are handled by Chrome.
ALLOWED_DOMAINS = (
    'woodmoodmobilya.com', 'facebook.com', 'instagram.com', 'linkedin.com',
    'pinterest.com', 'threads.com', 'threads.net', 'tumblr.com', 'x.com',
    'twitter.com', 'youtube.com', 'tiktok.com', 'accounts.google.com',
)


def validate_url(value):
    try:
        parts = urlsplit(value)
        host = (parts.hostname or '').lower()
        valid_host = any(host == d or host.endswith('.' + d) for d in ALLOWED_DOMAINS)
        if (parts.scheme != 'https' or not valid_host or parts.username or parts.password
                or parts.port not in (None, 443)):
            raise ValueError
    except ValueError:
        raise ValueError('Only configured social platform HTTPS URLs are allowed') from None
    return urlunsplit((parts.scheme, parts.netloc, parts.path or '/', parts.query, ''))


def check_token(header, expected):
    prefix = 'Bearer '
    return bool(header and header.startswith(prefix)
                and hmac.compare_digest(header[len(prefix):], expected))


def request_hash(kind, payload):
    return hashlib.sha256(json.dumps({'kind': kind, 'payload': payload}, sort_keys=True).encode()).hexdigest()
