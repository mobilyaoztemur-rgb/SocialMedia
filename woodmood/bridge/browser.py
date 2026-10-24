import asyncio
import uuid

from .journal import Journal
from .security import request_hash, validate_url


class OwnerControl(ValueError):
    pass


class BrowserFailure(Exception):
    pass


class Browser:
    def __init__(self, config):
        self.config = config
        config.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.journal = Journal(config.directory / 'operations.sqlite3')
        self.lock = asyncio.Lock()
        self.context = None
        self.playwright = None
        self.pages = {}

    @property
    def running(self):
        return bool(self.context and self.context.browser and self.context.browser.is_connected())

    @property
    def paused(self):
        return self.config.paused_file.exists()

    def require_agent(self):
        if self.paused:
            raise OwnerControl('Owner is controlling the browser. Wait until they release it locally.')

    async def start(self):
        from playwright.async_api import async_playwright
        self.playwright = await async_playwright().start()
        try:
            self.context = await self.playwright.chromium.launch_persistent_context(
                str(self.config.profile), executable_path=self.config.executable,
                headless=self.config.headless, chromium_sandbox=self.config.sandbox,
                accept_downloads=False, viewport={'width': 1440, 'height': 1000},
            )
            # Restrict document navigation initiated by automation or page scripts.
            async def guard(route):
                if (route.request.is_navigation_request() and route.request.frame.parent_frame is None
                        and route.request.url != 'about:blank'):
                    try:
                        validate_url(route.request.url)
                    except ValueError:
                        await route.abort()
                        return
                await route.continue_()
            await self.context.route('**/*', guard)
            if not self.context.pages:
                await self.context.new_page()
        except BaseException:
            await self.playwright.stop()
            self.playwright = None
            raise

    async def stop(self):
        try:
            if self.context:
                await self.context.close()
        finally:
            if self.playwright:
                await self.playwright.stop()

    def page(self, page_id):
        page = self.pages.get(page_id)
        if not page or page.is_closed():
            raise ValueError('Page ID not found; refresh the page list')
        return page

    def register(self, page):
        for key, existing in self.pages.items():
            if existing is page:
                return key
        key = uuid.uuid4().hex
        self.pages[key] = page
        return key

    async def list_pages(self):
        self.require_agent()
        async with self.lock:
            self.require_agent()
            return [{'id': self.register(p), 'url': p.url, 'title': await p.title()}
                    for p in self.context.pages if not p.is_closed()]

    async def run(self, key, kind, payload, function):
        self.require_agent()
        async with self.lock:
            self.require_agent()
            existing = self.journal.begin(key, request_hash(kind, payload), kind)
            if existing is not None:
                return existing
            try:
                result = await function()
            except ValueError:
                self.journal.finish(key, 'failed')
                raise
            except BaseException as exc:
                self.journal.finish(key, 'uncertain')
                if isinstance(exc, Exception):
                    raise BrowserFailure('Browser action failed; inspect the page before retrying') from None
                raise
            self.journal.finish(key, 'done', result)
            return result

    async def new_page(self, key, url):
        url = validate_url(url)
        async def execute():
            page = await self.context.new_page()
            await page.goto(url, wait_until='domcontentloaded', timeout=45000)
            return {'id': self.register(page), 'url': page.url, 'title': await page.title()}
        return await self.run(key, 'open', {'url': url}, execute)

    async def navigate(self, key, page_id, url):
        url = validate_url(url)
        async def execute():
            page = self.page(page_id)
            await page.goto(url, wait_until='domcontentloaded', timeout=45000)
            return {'id': page_id, 'url': page.url, 'title': await page.title()}
        return await self.run(key, 'navigate', {'page_id': page_id, 'url': url}, execute)

    async def snapshot(self, page_id):
        self.require_agent()
        async with self.lock:
            self.require_agent()
            page = self.page(page_id)
            # Password/input values are not exported. References expire after the next snapshot.
            token = uuid.uuid4().hex
            elements = await page.evaluate('''token => {
              document.querySelectorAll('[data-woodmood-ref]').forEach(el => el.removeAttribute('data-woodmood-ref'));
              const nodes = [...document.querySelectorAll('a,button,input,textarea,select,[role=button],[contenteditable=true]')]
                .filter(el => el.getClientRects().length).slice(0,250);
              return nodes.map((el,i) => {
                const ref=token+'-'+i; el.setAttribute('data-woodmood-ref',ref);
                return {selector:'[data-woodmood-ref="'+ref+'"]',tag:el.tagName.toLowerCase(),
                  role:el.getAttribute('role'),type:el.getAttribute('type'),
                  label:el.getAttribute('aria-label') || el.getAttribute('placeholder') ||
                        [...(el.labels || [])].map(x=>x.innerText).join(' ') || (el.innerText || '').slice(0,200),
                  disabled:!!el.disabled};
              });
            }''', token)
            text = await page.locator('body').inner_text(timeout=10000)
            return {'id': page_id, 'url': page.url, 'title': await page.title(),
                    'text': text[:20000], 'text_truncated': len(text) > 20000,
                    'elements': elements, 'element_limit': 250}

    async def screenshot(self, page_id):
        self.require_agent()
        async with self.lock:
            self.require_agent()
            return await self.page(page_id).screenshot(type='png', full_page=False)

    async def act(self, key, page_id, payload):
        async def execute():
            page = self.page(page_id)
            action = payload['action']
            selector = payload.get('selector')
            target = page.locator(selector) if selector else None
            if target is not None and await target.count() != 1:
                raise ValueError('Selector must identify exactly one element; take a fresh snapshot')
            if action == 'click':
                await target.click(timeout=15000)
            elif action == 'fill':
                await target.fill(payload['value'], timeout=15000)
            elif action == 'press':
                await target.press(payload['value'], timeout=15000)
            elif action == 'select':
                await target.select_option(value=payload['value'], timeout=15000)
            elif action == 'scroll':
                await page.mouse.wheel(0, payload.get('delta', 600))
            elif action == 'upload':
                files = []
                for media_id in payload['media_ids']:
                    path = self.config.directory / 'uploads' / media_id
                    if path.parent != self.config.directory / 'uploads' or not path.is_file():
                        raise ValueError('Unknown uploaded media ID')
                    files.append(str(path))
                await target.set_input_files(files, timeout=15000)
            return {'id': page_id, 'url': page.url, 'action': action, 'executed': True}
        return await self.run(key, 'action', {'page_id': page_id, **payload}, execute)
