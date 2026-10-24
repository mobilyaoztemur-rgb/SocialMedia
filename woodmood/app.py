from pathlib import Path
import sqlite3

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from .db import Store
from .media import prepare_project_media
from .settings import load_settings, PLATFORMS
from .source import scan
from .workflow import cancel_plan, edit_draft, generate_drafts, make_plan, ready_draft, set_order

STATIC = Path(__file__).parent / "static"


class OrderInput(BaseModel):
    order: int | None = Field(default=None, ge=1)


class CaptionInput(BaseModel):
    caption: str = Field(min_length=1, max_length=5000)


class PlanInput(BaseModel):
    first_at: str
    interval_hours: int = Field(ge=1, le=8760)
    count: int = Field(ge=1, le=100)


class DraftInput(BaseModel):
    refresh: bool = False


def create_app(config=None):
    config = config or load_settings()
    store = Store(config["data_dir"] / "woodmood.sqlite3")
    app = FastAPI(title="Woodmood Social", docs_url="/api/docs")
    app.state.store = store

    @app.middleware("http")
    async def local_write_guard(request: Request, call_next):
        # Local development UI only. Reject cross-origin form/JS writes (CSRF).
        host = request.headers.get("host", "").split(":")[0]
        if host not in {"127.0.0.1", "localhost", "testserver"}:
            return JSONResponse({"detail": "Local development server only"}, status_code=403)
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            if origin and origin != f"http://{request.headers.get('host')}":
                return JSONResponse({"detail": "Cross-origin writes are disabled"}, status_code=403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' https:; frame-ancestors 'none'"
        return response

    @app.exception_handler(ValueError)
    async def invalid(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=400)

    @app.exception_handler(sqlite3.IntegrityError)
    async def conflict(request, exc):
        return JSONResponse({"detail": "Sıra numarası başka bir projede kullanılıyor."}, status_code=409)

    @app.get("/")
    def index():
        return FileResponse(STATIC / "index.html")

    @app.get("/app.js")
    def script():
        return FileResponse(STATIC / "app.js", media_type="text/javascript")

    @app.get("/style.css")
    def stylesheet():
        return FileResponse(STATIC / "style.css", media_type="text/css")

    @app.get("/health")
    def health():
        with store.connect() as c:
            c.execute("SELECT 1").fetchone()
        return {"status": "ok", "publishing": "simulation_only"}

    @app.get("/api/state")
    def state():
        return {"projects": store.projects(), "drafts": store.drafts(), "events": store.history(),
                "latest_scan": store.latest_scan(), "mode": config["workflow"]["mode"],
                "timezone": config["workflow"]["timezone"], "publishing_enabled": False,
                "accounts": [{**a, "connected": False,
                              "drafts_supported": a["platform"] in config["workflow"]["platforms"]}
                             for a in config["accounts"]]}

    @app.post("/api/scan")
    def source_scan():
        try:
            result = scan(store, config["source"])
        except Exception as exc:
            raise HTTPException(502, "Kaynak taranamadı. Ağ iznini, canlı HTML yapısını ve seçicileri kontrol edin.") from exc
        result["drafts"] = generate_drafts(store, config["workflow"])
        return result

    @app.post("/api/drafts/generate")
    def generate(body: DraftInput):
        return generate_drafts(store, config["workflow"], body.refresh)

    @app.put("/api/projects/{project_id}/order")
    def order(project_id: int, body: OrderInput):
        set_order(store, project_id, body.order)
        return {"ok": True}

    @app.put("/api/drafts/{draft_id}")
    def edit(draft_id: int, body: CaptionInput):
        edit_draft(store, draft_id, body.caption)
        return {"ok": True}

    @app.post("/api/drafts/{draft_id}/ready")
    def ready(draft_id: int):
        ready_draft(store, draft_id)
        return {"ok": True}

    @app.post("/api/projects/{project_id}/media")
    def media(project_id: int):
        try:
            return {"files": prepare_project_media(store, config, project_id)}
        except ValueError:
            raise
        except Exception as exc:
            raise HTTPException(502, "Görseller hazırlanamadı; kaynak erişimini ve görsel biçimlerini kontrol edin.") from exc

    @app.post("/api/plans")
    def plan(body: PlanInput):
        return make_plan(store, config["workflow"], body.first_at, body.interval_hours, body.count)

    @app.get("/api/plans/{plan_id}")
    def get_plan(plan_id: int):
        import json
        with store.connect() as c:
            row = c.execute("SELECT * FROM plans WHERE id=?", (plan_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Plan not found")
        return {"plan_id": plan_id, **json.loads(row["content"])}

    @app.post("/api/plans/cancel")
    def cancel():
        return cancel_plan(store)

    return app
