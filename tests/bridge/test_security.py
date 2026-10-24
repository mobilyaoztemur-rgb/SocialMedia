import json
from pathlib import Path

import httpx
import pytest

from woodmood.bridge.config import BridgeConfig, ROOT, initialize
from woodmood.bridge.journal import Journal, OperationConflict
from woodmood.bridge.security import check_token, validate_url
from woodmood.remote import BridgeClient, validate_endpoint

TOKEN = 'test-token-with-at-least-32-characters'


@pytest.mark.parametrize('url', ['http://facebook.com', 'https://facebook.com.evil.example',
    'https://evilfacebook.com', 'https://u:p@facebook.com', 'https://localhost/',
    'https://127.0.0.1/', 'file:///etc/passwd', 'javascript:alert(1)', 'https://facebook.com:8443/'])
def test_navigation_rejects_unapproved_targets(url):
    with pytest.raises(ValueError):
        validate_url(url)


@pytest.mark.parametrize('url', ['https://www.facebook.com/mobilyawoodmood',
    'https://business.facebook.com/', 'https://accounts.google.com/',
    'https://tr.pinterest.com/mobilyawoodmood/', 'https://woodmoodmobilya.com/tr/projeler'])
def test_navigation_accepts_configured_sites(url):
    assert validate_url(url).startswith('https://')


def test_setup_is_repeatable_preserves_token_and_owner_release(tmp_path):
    initialize(tmp_path)
    cfg = BridgeConfig.load(tmp_path)
    assert cfg.paused_file.exists()
    original = cfg.token
    cfg.paused_file.unlink()
    initialize(tmp_path)
    assert BridgeConfig.load(tmp_path).token == original
    assert not cfg.paused_file.exists()
    assert original not in (tmp_path / 'bridge.json').read_text()


def test_profile_inside_checkout_is_rejected():
    with pytest.raises(ValueError, match='outside'):
        BridgeConfig(ROOT / 'var/unsafe-profile', TOKEN)


def test_bearer_token_must_match():
    assert check_token('Bearer ' + TOKEN, TOKEN)
    assert not check_token(None, TOKEN)
    assert not check_token('Bearer wrong', TOKEN)


def test_ambiguous_operation_is_not_replayed_after_restart(tmp_path):
    path = tmp_path / 'journal.sqlite3'
    journal = Journal(path)
    journal.begin('operation-1', 'fingerprint', 'click')
    reopened = Journal(path)
    assert reopened.get('operation-1')['state'] == 'uncertain'
    with pytest.raises(OperationConflict):
        reopened.begin('operation-1', 'fingerprint', 'click')


def test_same_operation_key_cannot_change_request(tmp_path):
    journal = Journal(tmp_path / 'journal.sqlite3')
    journal.begin('operation-1', 'fingerprint', 'click')
    journal.finish('operation-1', 'done', {'ok': True})
    assert journal.begin('operation-1', 'fingerprint', 'click') == {'ok': True}
    with pytest.raises(OperationConflict):
        journal.begin('operation-1', 'changed-fingerprint', 'click')


@pytest.mark.parametrize('url', ['http://example.com', 'https://u:p@example.com',
    'https://example.com/path', 'https://example.com/?token=x'])
def test_remote_origin_validation(url):
    with pytest.raises(ValueError):
        validate_endpoint(url)


def test_remote_client_never_follows_redirect_with_credentials():
    seen = []
    def respond(request):
        seen.append(request)
        return httpx.Response(302, headers={'location':'https://evil.example/'})
    client = BridgeClient('https://bridge.example', TOKEN, transport=httpx.MockTransport(respond))
    with pytest.raises(RuntimeError, match='redirected'):
        client.request('GET','/v1/health')
    assert len(seen) == 1
    client.close()


def test_remote_mutations_get_operation_id_and_do_not_retry():
    seen=[]
    def respond(request):
        seen.append(request)
        return httpx.Response(502,json={'detail':'Unknown action outcome'})
    client=BridgeClient('https://bridge.example',TOKEN,transport=httpx.MockTransport(respond))
    with pytest.raises(RuntimeError,match='502'):
        client.request('POST','/v1/pages',{'url':'https://facebook.com'})
    assert len(seen)==1 and seen[0].headers['idempotency-key']
    assert TOKEN not in str(seen[0].url)
    client.close()


def test_remote_client_sends_access_credentials_only_to_fixed_origin():
    seen=[]
    def respond(request):
        seen.append(request)
        return httpx.Response(200,json={'ok':True})
    client=BridgeClient('https://bridge.example',TOKEN,'cf-id','cf-secret',transport=httpx.MockTransport(respond))
    client.request('GET','/v1/health')
    assert seen[0].headers['cf-access-client-id']=='cf-id'
    assert seen[0].headers['cf-access-client-secret']=='cf-secret'
    for path in ['https://evil.example/v1/x','//evil.example/v1/x','/v1/../other']:
        with pytest.raises(ValueError):client.request('GET',path)
    assert len(seen)==1
    client.close()
