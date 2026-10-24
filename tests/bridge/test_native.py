import asyncio
from dataclasses import replace
import json
import os
import shutil

import pytest

from woodmood.bridge.config import BridgeConfig, find_chrome, initialize
from woodmood.bridge.native import chrome_arguments

TOKEN='native-test-token-at-least-32-characters'


def test_manual_sign_in_has_no_driver_or_debugging_switches(tmp_path):
    cfg=BridgeConfig(tmp_path,TOKEN,executable='/test/chrome')
    args=chrome_arguments(cfg,debugging=False)
    assert '--user-data-dir='+str(cfg.profile) in args
    assert not any('remote-debugging' in arg or 'enable-automation' in arg for arg in args)
    assert '--no-sandbox' not in args
    controlled=chrome_arguments(cfg,debugging=True)
    assert '--remote-debugging-address=127.0.0.1' in controlled
    assert '--remote-debugging-port=0' in controlled
    assert not any('ignore-certificate' in arg or 'disable-web-security' in arg for arg in controlled)


def test_old_config_loads_new_connection_mode_without_resetting_state(tmp_path):
    initialize(tmp_path)
    before=BridgeConfig.load(tmp_path)
    config_path=tmp_path/'bridge.json'
    old=json.loads(config_path.read_text());old.pop('connection_mode')
    config_path.write_text(json.dumps(old))
    after=BridgeConfig.load(tmp_path)
    assert after.connection_mode=='native'
    assert after.token==before.token and after.profile==before.profile


def test_cookie_profile_survives_controlled_to_native_transition(tmp_path):
    from woodmood.bridge.browser import Browser
    executable=os.environ.get('WOODMOOD_TEST_CHROME') or shutil.which('chromium') or find_chrome()
    assert executable,'A real Chromium executable is required'
    cfg=BridgeConfig(tmp_path,TOKEN,executable=executable,headless=True,sandbox=False,connection_mode='playwright')
    async def exercise():
        first=Browser(cfg)
        await first.start()
        try:
            await first.context.add_cookies([{'name':'test-profile-transition','value':'synthetic-only',
                    'url':'https://woodmoodmobilya.com','expires':4102444800}])
        finally:
            await first.stop()
        second=Browser(replace(cfg,connection_mode='native'))
        await second.start()
        try:
            assert second.running
            cookies=await second.context.cookies('https://woodmoodmobilya.com')
            assert any(c['name']=='test-profile-transition' and c['value']=='synthetic-only' for c in cookies)
        finally:
            await second.stop()
    asyncio.run(exercise())
