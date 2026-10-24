import json
from pathlib import Path
import subprocess

import pytest

from woodmood.bridge.config import BridgeConfig
from woodmood.bridge.tunnel import configure_named_tunnel

ID='11111111-2222-4333-8444-555555555555'
TOKEN='test-bridge-token-more-than-32-characters'


@pytest.fixture
def configured(tmp_path):
    private=tmp_path/'private';private.mkdir()
    cfg=BridgeConfig(private,TOKEN)
    credentials=tmp_path/(ID+'.json')
    credentials.write_text('{"synthetic":"test-only"}')
    return cfg,credentials


def test_named_config_is_private_repeatable_and_uses_loopback(configured):
    cfg,creds=configured
    path=configure_named_tunnel(cfg,ID,'kontrol.example.com',creds)
    first=path.read_bytes()
    assert configure_named_tunnel(cfg,ID,'kontrol.example.com',creds)==path
    assert path.read_bytes()==first
    data=json.loads(first)
    assert data['ingress'][0]['service']=='http://127.0.0.1:8787'
    assert data['ingress'][0]['originRequest']['httpHostHeader']=='localhost'
    assert data['ingress'][-1]['service']=='http_status:404'
    assert TOKEN not in path.read_text() and 'synthetic' not in path.read_text()


@pytest.mark.parametrize('hostname',['https://example.com','example.com/path','*.example.com','example.com:443','-bad.example.com'])
def test_invalid_hostname_does_not_write_config(configured,hostname):
    cfg,creds=configured
    with pytest.raises(ValueError):configure_named_tunnel(cfg,ID,hostname,creds)
    assert not (cfg.directory/'tunnel.yml').exists()


def test_existing_custom_config_is_not_overwritten(configured):
    cfg,creds=configured
    path=cfg.directory/'tunnel.yml';path.write_text('custom: preserved\n')
    with pytest.raises(ValueError,match='preserved'):
        configure_named_tunnel(cfg,ID,'kontrol.example.com',creds)
    assert path.read_text()=='custom: preserved\n'


def test_missing_credentials_does_not_produce_a_ready_config(configured):
    cfg,creds=configured;creds.unlink()
    with pytest.raises(ValueError,match='not found'):
        configure_named_tunnel(cfg,ID,'kontrol.example.com',creds)
