from fastapi.testclient import TestClient
from woodmood.app import create_app
from woodmood.source import upsert_projects


def test_empty_dashboard_and_accounts(cfg):
    with TestClient(create_app(cfg)) as c:
        assert c.get('/').status_code == 200
        assert 'Projelerinize' in c.get('/').text
        state = c.get('/api/state').json()
        assert state['projects'] == []
        assert len(state['accounts']) == 9
        assert not any(a['connected'] for a in state['accounts'])
        assert sum(a['drafts_supported'] for a in state['accounts']) == 3
        assert c.get('/health').json()['publishing'] == 'simulation_only'


def test_functional_request_generates_platform_drafts_and_plan(cfg, project):
    app = create_app(cfg)
    upsert_projects(app.state.store, [project])
    with TestClient(app) as c:
        assert c.post('/api/drafts/generate', json={}).json()['created'] == 3
        response = c.post('/api/plans', json={'first_at':'2099-01-01T12:00:00+03:00', 'interval_hours':48,'count':1})
        assert response.status_code == 200
        assert len(response.json()['items']) == 3
        assert c.get('/api/plans/1').json()['simulation_only'] is True
        assert c.post('/api/plans/cancel').json()['cancelled'] == 3


def test_cross_origin_write_and_unknown_host_rejected(cfg):
    with TestClient(create_app(cfg)) as c:
        assert c.post('/api/scan',headers={'origin':'https://evil.example'}).status_code == 403
        assert c.get('/api/state',headers={'host':'evil.example'}).status_code == 403


def test_failed_scan_is_visible_without_fake_project_data(cfg, monkeypatch):
    from woodmood import source
    def fail(self, url):
        raise OSError('offline')
    monkeypatch.setattr(source.Fetcher, 'get', fail)
    with TestClient(create_app(cfg)) as c:
        assert c.post('/api/scan').status_code == 502
        state = c.get('/api/state').json()
        assert state['projects'] == []
        assert state['latest_scan']['status'] == 'failed'


def test_bad_order_and_plan_inputs_rejected(cfg):
    with TestClient(create_app(cfg)) as c:
        assert c.put('/api/projects/1/order',json={'order':-1}).status_code == 422
        assert c.post('/api/plans',json={'first_at':'2099-01-01', 'interval_hours':0,'count':1}).status_code == 422
