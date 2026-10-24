from datetime import datetime, timedelta, timezone
import json

from .db import now
from .settings import PLATFORMS


def caption_for(project, platform):
    title = project["title"]
    # Deterministic copy uses only source facts; no invented materials, location, or client names.
    description = " ".join(project["description"].split())[:650]
    if platform == "instagram":
        text = f"{title}\n\n{description}\n\nProjenin tüm detayları web sitemizde.\n\n#Woodmood #Mobilya #İçMimari #Proje"
    elif platform == "facebook":
        text = f"Woodmood projelerinden: {title}\n\n{description}\n\nProjeyi inceleyin: {project['url']}\n\n#Woodmood #Mobilya"
    elif platform == "linkedin":
        text = f"Proje portföyümüzden | {title}\n\n{description}\n\nProje detayları: {project['url']}\n\n#Woodmood #İçMimari #MobilyaTasarımı"
    else:
        raise ValueError("Unsupported platform")
    return text.strip()


def generate_drafts(store, cfg, refresh=False):
    created = updated = 0
    with store.connect() as c:
        for p in store.projects():
            for platform in cfg["platforms"]:
                old = c.execute("SELECT * FROM drafts WHERE project_id=? AND platform=?",
                                (p["id"], platform)).fetchone()
                if old and not refresh:
                    continue
                if old and old["status"] == "scheduled":
                    raise ValueError("Cancel the existing plan before refreshing scheduled drafts")
                caption = caption_for(p, platform)
                status = "ready" if cfg["mode"] == "automatic" else "draft"
                stamp = now()
                c.execute("""INSERT INTO drafts(project_id,platform,caption,images,source_fingerprint,
                   status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)
                   ON CONFLICT(project_id,platform) DO UPDATE SET caption=excluded.caption,
                   images=excluded.images,source_fingerprint=excluded.source_fingerprint,
                   status=excluded.status,scheduled_at=NULL,updated_at=excluded.updated_at""",
                          (p["id"], platform, caption, json.dumps(p["images"]), p["fingerprint"],
                           status, stamp, stamp))
                created += old is None
                updated += old is not None
            if refresh:
                c.execute("UPDATE projects SET needs_review=0 WHERE id=?", (p["id"],))
        store.event(c, "drafts_generated", {"created": created, "updated": updated})
    return {"created": created, "updated": updated}


def set_order(store, project_id, order):
    with store.connect() as c:
        if c.execute("SELECT 1 FROM drafts WHERE status='scheduled'").fetchone():
            raise ValueError("Cancel the current plan before changing project order")
        result = c.execute("UPDATE projects SET manual_order=? WHERE id=?", (order, project_id))
        if not result.rowcount:
            raise ValueError("Project not found")
        store.event(c, "order_changed", {"project_id": project_id, "manual_order": order})


def edit_draft(store, draft_id, caption):
    with store.connect() as c:
        d = c.execute("SELECT * FROM drafts WHERE id=?", (draft_id,)).fetchone()
        if not d:
            raise ValueError("Draft not found")
        if d["status"] == "scheduled":
            raise ValueError("Cancel the current plan before editing a scheduled draft")
        if not caption.strip() or len(caption) > PLATFORMS[d["platform"]]["limit"]:
            raise ValueError("Caption is empty or exceeds the configured platform limit")
        c.execute("UPDATE drafts SET caption=?,status='draft',updated_at=? WHERE id=?",
                  (caption.strip(), now(), draft_id))
        store.event(c, "draft_edited", {"draft_id": draft_id})


def ready_draft(store, draft_id):
    with store.connect() as c:
        d = c.execute("""SELECT d.*, p.fingerprint, p.needs_review FROM drafts d
                       JOIN projects p ON p.id=d.project_id WHERE d.id=?""", (draft_id,)).fetchone()
        if not d:
            raise ValueError("Draft not found")
        if d["source_fingerprint"] != d["fingerprint"] or d["needs_review"]:
            raise ValueError("Source changed; regenerate drafts before marking ready")
        if d["status"] == "scheduled":
            raise ValueError("Draft is already scheduled")
        c.execute("UPDATE drafts SET status='ready',updated_at=? WHERE id=?", (now(), draft_id))
        store.event(c, "draft_ready", {"draft_id": draft_id})


def make_plan(store, cfg, first_at, interval_hours, count):
    """Persist a simulation, never call a social network or mark anything as published."""
    start = datetime.fromisoformat(first_at.replace("Z", "+00:00"))
    if start.tzinfo is None:
        raise ValueError("Start time requires a timezone offset")
    start = start.astimezone(timezone.utc)
    if start <= datetime.now(timezone.utc):
        raise ValueError("Start time must be in the future")
    if not 1 <= interval_hours <= 8760 or not 1 <= count <= 100:
        raise ValueError("Interval must be 1–8760 hours; project count must be 1–100")
    # Acquire a write lock before reading eligibility. Concurrent planners cannot duplicate slots.
    with store.connect() as c:
        c.execute("BEGIN IMMEDIATE")
        projects = [store.decode_project(r) for r in c.execute("SELECT * FROM projects")]
        drafts = [dict(r) for r in c.execute("SELECT * FROM drafts")]
        pending = []
        for p in projects:
            pd = [d for d in drafts if d["project_id"] == p["id"] and d["platform"] in cfg["platforms"]]
            if len(pd) == len(cfg["platforms"]) and all(d["status"] == "scheduled" for d in pd):
                continue
            pending.append((p, pd))
        if not pending:
            raise ValueError("No unscheduled projects; scan and generate drafts first")
        if all(p["manual_order"] is not None for p, _ in pending):
            pending.sort(key=lambda item: item[0]["manual_order"])
            ordering = "manual"
        elif all(p["published_at"] is not None and p["manual_order"] is None for p, _ in pending):
            pending.sort(key=lambda item: (item[0]["published_at"], item[0]["id"]))
            ordering = "source_date"
        else:
            raise ValueError("Oldest-first order is unknown: supply dates or set a unique manual order for every pending project")
        latest = c.execute("SELECT max(scheduled_at) FROM drafts WHERE status='scheduled'").fetchone()[0]
        if latest and start <= datetime.fromisoformat(latest):
            raise ValueError("New slots must start after the existing plan")
        items = []
        for i, (p, pd) in enumerate(pending[:count]):
            if p["needs_review"]:
                raise ValueError("Source changed; refresh drafts before planning")
            if len(pd) != len(cfg["platforms"]) or any(d["status"] != "ready" for d in pd):
                raise ValueError(f"Project {p['id']} needs ready drafts for all configured platforms")
            stamp = (start + timedelta(hours=interval_hours * i)).isoformat()
            for d in pd:
                if d["source_fingerprint"] != p["fingerprint"]:
                    raise ValueError("Stale source fingerprint")
                c.execute("UPDATE drafts SET status='scheduled',scheduled_at=?,updated_at=? WHERE id=?",
                          (stamp, now(), d["id"]))
                items.append({"draft_id": d["id"], "project_id": p["id"], "platform": d["platform"],
                              "scheduled_at": stamp, "caption": d["caption"],
                              "source_images": json.loads(d["images"]),
                              "target_size": list(PLATFORMS[d["platform"]]["size"]),
                              "delivery": "simulation_only", "media_prepared": False})
        result = {"simulation_only": True, "ordering": ordering,
                  "interval_hours": interval_hours, "items": items}
        plan_id = c.execute("INSERT INTO plans(created_at,content) VALUES(?,?)",
                            (now(), json.dumps(result, ensure_ascii=False))).lastrowid
        store.event(c, "simulation_plan_created", {"plan_id": plan_id, "posts": len(items)})
        return {"plan_id": plan_id, **result}


def cancel_plan(store):
    with store.connect() as c:
        n = c.execute("UPDATE drafts SET status='ready',scheduled_at=NULL,updated_at=? WHERE status='scheduled'",
                      (now(),)).rowcount
        store.event(c, "simulation_plan_cancelled", {"drafts": n})
    return {"cancelled": n}
