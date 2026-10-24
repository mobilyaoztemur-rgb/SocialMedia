import socket
import sys

import pytest

from woodmood.bridge.config import BridgeConfig, initialize
from woodmood.bridge.local import port_available, require_manual_access

TOKEN='local-test-token-longer-than-32-characters'


@pytest.fixture
def local_listener():
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as listener:
        listener.bind(('127.0.0.1',0));listener.listen(1)
        yield listener.getsockname()[1]


def test_local_probe_detects_an_unresponsive_listener_without_http(local_listener):
    assert not port_available(local_listener)


def test_manual_launch_is_blocked_by_occupied_bridge_port(tmp_path,local_listener):
    cfg=BridgeConfig(tmp_path,TOKEN,port=local_listener,executable='/test/chrome')
    with pytest.raises(SystemExit,match='port is in use'):
        require_manual_access(cfg)


def test_stale_marker_with_live_debug_port_does_not_allow_manual_launch(tmp_path,local_listener):
    with socket.socket() as s:
        s.bind(('127.0.0.1',0));bridge_port=s.getsockname()[1]
    cfg=BridgeConfig(tmp_path,TOKEN,port=bridge_port,executable='/test/chrome')
    cfg.profile.mkdir()
    (cfg.profile/'DevToolsActivePort').write_text(str(local_listener)+'\n/devtools/browser/synthetic-test\n')
    with pytest.raises(SystemExit,match='may still be open'):
        require_manual_access(cfg)


def test_owner_browser_no_longer_calls_timing_out_http_probe(tmp_path,monkeypatch,capsys):
    from woodmood.bridge import __main__ as cli
    from woodmood.bridge import native
    import httpx
    initialize(tmp_path)
    token=(tmp_path/'bridge-token').read_text()
    launches=[]
    def fail_if_http_called(*args,**kwargs):
        raise AssertionError('Manual sign-in must not call an HTTP health probe')
    monkeypatch.setattr(httpx.Client,'get',fail_if_http_called)
    monkeypatch.setattr(native,'launch',lambda cfg,**kw:launches.append((cfg,kw)))
    monkeypatch.setattr(sys,'argv',['woodmood.bridge','--directory',str(tmp_path),'owner','browser'])
    cli.main()
    assert len(launches)==1 and launches[0][1]=={'debugging':False}
    assert (tmp_path/'owner-control').exists()
    assert (tmp_path/'bridge-token').read_text()==token
    assert token.strip() not in capsys.readouterr().out


def test_owner_pause_timeout_has_actionable_message_and_stays_paused(tmp_path,monkeypatch):
    from woodmood.bridge import __main__ as cli
    from woodmood.bridge import local
    import httpx
    initialize(tmp_path)
    monkeypatch.setattr(local,'port_available',lambda port:False)
    def timeout(*args,**kwargs):
        raise httpx.ConnectTimeout('synthetic timeout')
    monkeypatch.setattr(httpx.Client,'get',timeout)
    monkeypatch.setattr(sys,'argv',['woodmood.bridge','--directory',str(tmp_path),'owner','begin'])
    with pytest.raises(SystemExit,match='health check failed'):
        cli.main()
    assert (tmp_path/'owner-control').exists()
