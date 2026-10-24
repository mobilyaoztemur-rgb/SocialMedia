from contextlib import asynccontextmanager
from io import BytesIO
import re
import uuid

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from PIL import Image
from pydantic import BaseModel, Field, model_validator
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .browser import Browser, BrowserFailure, OwnerControl
from .journal import OperationConflict
from .security import check_token

MAX_UPLOAD = 25_000_000


class Navigate(BaseModel):
    url: str = Field(max_length=4000)


class Action(BaseModel):
    action: str = Field(pattern='^(click|fill|press|select|scroll|upload)$')
    selector: str | None = Field(default=None, min_length=1, max_length=2000)
    value: str | None = Field(default=None, max_length=20000)
    delta: int = Field(default=600, ge=-5000, le=5000)
    media_ids: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode='after')
    def complete(self):
        if self.action != 'scroll' and not self.selector:
            raise ValueError('This action needs a selector from a fresh snapshot')
        if self.action in ('fill', 'press', 'select') and self.value is None:
            raise ValueError('This action needs a value')
        if self.action == 'upload' and (not self.media_ids or any(
                not re.fullmatch(r'[a-f0-9]{32}\.(jpg|png|webp|mp4)', x) for x in self.media_ids)):
            raise ValueError('Use IDs returned by the media upload endpoint')
        return self


def operation_id(value):
    if not value or not re.fullmatch(r'[a-zA-Z0-9_-]{8,100}', value):
        raise HTTPException(400, 'A unique Idempotency-Key (8–100 characters) is required')
    return value


def create_app(config, browser=None):
    browser = browser or Browser(config)

    @asynccontextmanager
    async def lifespan(app):
        await browser.start()
        try:
            yield
        finally:
            await browser.stop()

    app = FastAPI(title='Woodmood PC Bridge', docs_url=None, redoc_url=None,
                  openapi_url=None, lifespan=lifespan)
    app.state.browser = browser

    @app.middleware('http')
    async def authenticate(request: Request, call_next):
        if not check_token(request.headers.get('authorization'), config.token):
            return JSONResponse({'detail': 'Authentication required'}, status_code=401,
                                headers={'WWW-Authenticate': 'Bearer'})
        # Browsers on unrelated sites cannot issue authenticated cross-origin calls.
        origin = request.headers.get('origin')
        if origin:
            return JSONResponse({'detail': 'Browser-origin requests are disabled; use the control client'}, status_code=403)
        length = request.headers.get('content-length')
        if length:
            try:
                if int(length) < 0 or int(length) > MAX_UPLOAD:
                    return JSONResponse({'detail': 'Request exceeds size limit'}, status_code=413)
            except ValueError:
                return JSONResponse({'detail': 'Invalid Content-Length'}, status_code=400)
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    allowed = ['localhost', '127.0.0.1']
    if config.public_host:
        allowed.append(config.public_host)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed)

    @app.exception_handler(OwnerControl)
    async def owner(request, exc):
        return JSONResponse({'detail': str(exc)}, status_code=423)

    @app.exception_handler(OperationConflict)
    async def ambiguous(request, exc):
        return JSONResponse({'detail': str(exc)}, status_code=409)

    @app.exception_handler(ValueError)
    async def invalid(request, exc):
        return JSONResponse({'detail': str(exc)}, status_code=400)

    @app.exception_handler(BrowserFailure)
    async def failure(request, exc):
        # Driver exceptions can contain text typed into the page; do not return them.
        return JSONResponse({'detail': 'Browser action failed or its outcome is uncertain. Inspect the page before retrying.'}, status_code=502)

    @app.get('/v1/health')
    async def health():
        return {'service': 'woodmood-pc-bridge', 'version': 1,
                'browser_running': browser.running,
                'owner_paused': browser.paused, 'busy': browser.lock.locked()}

    @app.get('/v1/pages')
    async def pages():
        return {'pages': await browser.list_pages()}

    @app.post('/v1/pages')
    async def new_page(body: Navigate, idempotency_key: str | None = Header(default=None)):
        return await browser.new_page(operation_id(idempotency_key), body.url)

    @app.post('/v1/pages/{page_id}/navigate')
    async def navigate(page_id: str, body: Navigate, idempotency_key: str | None = Header(default=None)):
        return await browser.navigate(operation_id(idempotency_key), page_id, body.url)

    @app.get('/v1/pages/{page_id}/snapshot')
    async def snapshot(page_id: str):
        return await browser.snapshot(page_id)

    @app.get('/v1/pages/{page_id}/screenshot')
    async def screenshot(page_id: str):
        return Response(await browser.screenshot(page_id), media_type='image/png')

    @app.post('/v1/pages/{page_id}/actions')
    async def act(page_id: str, body: Action, idempotency_key: str | None = Header(default=None)):
        return await browser.act(operation_id(idempotency_key), page_id, body.model_dump())

    @app.post('/v1/media')
    async def upload(request: Request):
        browser.require_agent()
        data = bytearray()
        async for chunk in request.stream():
            data.extend(chunk)
            if len(data) > MAX_UPLOAD:
                raise HTTPException(413, 'Media exceeds 25 MB')
        content_type = request.headers.get('content-type', '').split(';')[0]
        extensions = {'image/jpeg': 'jpg', 'image/png': 'png', 'image/webp': 'webp', 'video/mp4': 'mp4'}
        extension = extensions.get(content_type)
        if not extension:
            raise HTTPException(415, 'JPEG, PNG, WebP or MP4 required')
        if extension == 'mp4':
            if len(data) < 12 or data[4:8] != b'ftyp':
                raise HTTPException(415, 'Invalid MP4 container signature')
        else:
            try:
                with Image.open(BytesIO(data)) as image:
                    if image.format != {'jpg': 'JPEG', 'png': 'PNG', 'webp': 'WEBP'}[extension]:
                        raise ValueError
                    image.verify()
            except Exception:
                raise HTTPException(415, 'Invalid image file') from None
        media_id = uuid.uuid4().hex + '.' + extension
        folder = config.directory / 'uploads'
        folder.mkdir(mode=0o700, exist_ok=True)
        path = folder / media_id
        import os
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
        return {'media_id': media_id, 'bytes': len(data)}

    @app.get('/v1/operations/{key}')
    async def get_operation(key: str):
        entry = browser.journal.get(key)
        if not entry:
            raise HTTPException(404, 'Operation not found')
        return entry

    return app
