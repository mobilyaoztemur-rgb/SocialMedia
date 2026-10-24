"""Actual Chromium checks with explicitly synthetic website responses, no account login."""
from io import BytesIO
import json
import os
import shutil

from fastapi.testclient import TestClient
from PIL import Image
import pytest

from woodmood.bridge.app import create_app
from woodmood.bridge.browser import Browser
from woodmood.bridge.config import BridgeConfig, find_chrome

TOKEN='actual-browser-test-token-32-characters-long'
URL='https://woodmoodmobilya.com/tr/projeler/bridge-test-fixture'
HTML='''<!doctype html><html><head><title>Bridge test fixture</title></head><body>
<h1>Synthetic bridge fixture</h1><label>Caption<input id="caption"></label>
<input id="password" type="password" value="must-not-appear-in-snapshot">
<button id="save" onclick="document.querySelector('#result').textContent = document.querySelector('#caption').value; window.count=(window.count||0)+1">Save</button>
<div id="result"></div><input type="file" id="photo"><script>window.count=0;</script>
</body></html>'''


class FixtureBrowser(Browser):
    async def start(self):
        await super().start()
        async def fixture(route):
            await route.fulfill(status=200,content_type='text/html',body=HTML)
        # Replace only this test URL. Other navigation is governed by the real guard.
        await self.context.route(URL, fixture)


@pytest.fixture(params=['playwright', 'native'])
def bridge(tmp_path, request):
    executable=os.environ.get('WOODMOOD_TEST_CHROME') or shutil.which('chromium') or find_chrome()
    if not executable:
        pytest.fail('A real Chrome/Chromium executable is required for bridge readiness tests')
    cfg=BridgeConfig(tmp_path,TOKEN,executable=executable,headless=True,sandbox=False,connection_mode=request.param)
    browser=FixtureBrowser(cfg)
    app=create_app(cfg,browser)
    with TestClient(app,base_url='http://localhost') as client:
        client.headers['Authorization']='Bearer '+TOKEN
        yield client,browser,cfg


def post(client,path,body,key):
    return client.post(path,json=body,headers={'Idempotency-Key':key})


def open_page(client,key='open-test-page'):
    response=post(client,'/v1/pages',{'url':URL},key)
    assert response.status_code==200,response.text
    return response.json()['id']


def test_authentication_owner_pause_and_host_guard(bridge):
    client,browser,cfg=bridge
    assert client.get('/v1/health').json()['browser_running'] is True
    assert client.get('/v1/health',headers={'Authorization':'Bearer wrong'}).status_code==401
    assert client.get('/v1/pages',headers={'Authorization':''}).status_code==401
    assert client.get('/v1/health',headers={'Host':'evil.example'}).status_code==400
    assert client.get('/v1/health',headers={'Origin':'https://evil.example'}).status_code==403
    cfg.paused_file.touch()
    assert client.get('/v1/health').json()['owner_paused'] is True
    assert client.get('/v1/pages').status_code==423
    assert post(client,'/v1/pages',{'url':URL},'blocked-owner-open').status_code==423
    cfg.paused_file.unlink()
    assert client.get('/v1/pages').status_code==200


def test_real_browser_snapshot_fill_click_screenshot_and_operation_replay(bridge):
    client,browser,cfg=bridge
    page_id=open_page(client)
    snapshot=client.get(f'/v1/pages/{page_id}/snapshot').json()
    assert snapshot['title']=='Bridge test fixture'
    assert 'must-not-appear-in-snapshot' not in json.dumps(snapshot)
    body={'action':'fill','selector':'#caption','value':'Woodmood test caption'}
    assert post(client,f'/v1/pages/{page_id}/actions',body,'fill-caption-1').status_code==200
    click={'action':'click','selector':'#save'}
    assert post(client,f'/v1/pages/{page_id}/actions',click,'save-click-1').status_code==200
    assert post(client,f'/v1/pages/{page_id}/actions',click,'save-click-1').status_code==200
    assert client.portal.call(lambda: browser.page(page_id).evaluate('window.count'))==1
    assert 'Woodmood test caption' in client.get(f'/v1/pages/{page_id}/snapshot').json()['text']
    shot=client.get(f'/v1/pages/{page_id}/screenshot')
    assert shot.status_code==200 and shot.headers['content-type']=='image/png'
    with Image.open(BytesIO(shot.content)) as image: assert image.width > 500
    operation=client.get('/v1/operations/save-click-1').json()
    assert operation['state']=='done' and 'value' not in operation
    assert b'Woodmood test caption' not in (cfg.directory/'operations.sqlite3').read_bytes()


def test_media_upload_uses_real_file_input_and_no_arbitrary_files(bridge):
    client,browser,cfg=bridge
    page_id=open_page(client)
    image=BytesIO();Image.new('RGB',(20,20),'#008800').save(image,'JPEG')
    uploaded=client.post('/v1/media',content=image.getvalue(),headers={'Content-Type':'image/jpeg'})
    assert uploaded.status_code==200
    media_id=uploaded.json()['media_id']
    result=post(client,f'/v1/pages/{page_id}/actions',
                {'action':'upload','selector':'#photo','media_ids':[media_id]},'upload-photo-1')
    assert result.status_code==200
    assert client.portal.call(lambda: browser.page(page_id).locator('#photo').evaluate('(el)=>el.files.length'))==1
    assert post(client,f'/v1/pages/{page_id}/actions',
                {'action':'upload','selector':'#photo','media_ids':['../../etc/passwd']},'bad-upload-1').status_code==422
    assert client.post('/v1/media',content=b'not an image',headers={'Content-Type':'image/jpeg'}).status_code==415


def test_browser_rejects_bad_targets_and_requires_operation_id(bridge):
    client,browser,cfg=bridge
    assert post(client,'/v1/pages',{'url':'http://127.0.0.1/'},'bad-target-1').status_code==400
    assert client.post('/v1/pages',json={'url':URL}).status_code==400
    assert client.post('/v1/media',content=b'x',headers={'Content-Type':'text/html'}).status_code==415
    assert client.get('/docs').status_code==404
    assert client.get('/openapi.json').status_code==404


def test_owner_pause_blocks_existing_page_read_and_write(bridge):
    client,browser,cfg=bridge
    page_id=open_page(client)
    cfg.paused_file.touch()
    for path in ('snapshot','screenshot'):
        assert client.get(f'/v1/pages/{page_id}/{path}').status_code==423
    assert post(client,f'/v1/pages/{page_id}/actions',
                {'action':'click','selector':'#save'},'owner-block-click').status_code==423


def test_browser_profile_restores_cookies_and_local_storage(bridge):
    client,browser,cfg=bridge
    page_id=open_page(client)
    async def persist():
        await browser.context.add_cookies([{'name':'fixture-session','value':'synthetic-test-only',
                                          'url':'https://woodmoodmobilya.com','expires':4102444800}])
        await browser.page(page_id).evaluate("localStorage.setItem('fixture-owner','synthetic-test-only')")
        await browser.stop()
        await browser.start()
        cookies=await browser.context.cookies('https://woodmoodmobilya.com')
        p=await browser.context.new_page()
        await p.goto(URL)
        stored=await p.evaluate("localStorage.getItem('fixture-owner')")
        return cookies,stored
    cookies,stored=client.portal.call(persist)
    assert any(c['name']=='fixture-session' and c['value']=='synthetic-test-only' for c in cookies)
    assert stored=='synthetic-test-only'
