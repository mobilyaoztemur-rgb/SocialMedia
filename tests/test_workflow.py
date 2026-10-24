from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from io import BytesIO
import pytest
from PIL import Image
from woodmood.media import render_image
from woodmood.source import upsert_projects
from woodmood.workflow import cancel_plan, edit_draft, generate_drafts, make_plan, ready_draft, set_order

START = "2099-01-01T12:00:00+03:00"


def seeded(store, cfg, project):
    upsert_projects(store, [project])
    generate_drafts(store, cfg["workflow"])


def test_automatic_drafts_distinct_and_repeatable(store, cfg, project):
    seeded(store, cfg, project)
    drafts = store.drafts()
    assert len(drafts) == 3
    assert len({d["caption"] for d in drafts}) == 3
    assert all(d["status"] == "ready" for d in drafts)
    assert generate_drafts(store, cfg["workflow"]) == {"created": 0, "updated": 0}


def test_oldest_first_not_discovery_order(store, cfg, project):
    newer = {**project, "url": project["url"] + "-new", "published_at": "2025-01-01T00:00:00+00:00"}
    upsert_projects(store, [newer, project])
    generate_drafts(store, cfg["workflow"])
    plan = make_plan(store, cfg["workflow"], START, 48, 2)
    assert plan["simulation_only"] is True
    assert [i["project_id"] for i in plan["items"]] == [2, 2, 2, 1, 1, 1]
    assert plan["items"][0]["scheduled_at"] == "2099-01-01T09:00:00+00:00"
    assert plan["items"][3]["scheduled_at"] == "2099-01-03T09:00:00+00:00"
    assert all(d["status"] == "scheduled" for d in store.drafts())
    with pytest.raises(ValueError, match="No unscheduled"):
        make_plan(store, cfg["workflow"], START, 48, 2)


def test_unknown_date_requires_explicit_order(store, cfg, project):
    seeded(store, cfg, {**project, "published_at": None})
    with pytest.raises(ValueError, match="order is unknown"):
        make_plan(store, cfg["workflow"], START, 48, 1)
    set_order(store, 1, 1)
    assert make_plan(store, cfg["workflow"], START, 48, 1)["ordering"] == "manual"


def test_source_update_invalidates_plan_without_erasing_edited_caption(store, cfg, project):
    seeded(store, cfg, project)
    edit_draft(store, 1, "Elle düzenlenmiş metin")
    ready_draft(store, 1)
    make_plan(store, cfg["workflow"], START, 24, 1)
    upsert_projects(store, [{**project, "fingerprint": "new-fingerprint", "description": "Güncel kaynak"}])
    assert all(d["status"] == "draft" and d["scheduled_at"] is None for d in store.drafts())
    assert store.drafts()[0]["caption"] == "Elle düzenlenmiş metin"
    with pytest.raises(ValueError, match="Source changed"):
        ready_draft(store, 1)
    generate_drafts(store, cfg["workflow"], refresh=True)
    assert not store.projects()[0]["needs_review"]
    assert all("Güncel kaynak" in d["caption"] for d in store.drafts())


def test_review_mode_and_unready_draft_prevent_plan(store, cfg, project):
    cfg["workflow"]["mode"] = "review"
    seeded(store, cfg, project)
    with pytest.raises(ValueError, match="needs ready drafts"):
        make_plan(store, cfg["workflow"], START, 24, 1)
    assert all(d["status"] == "draft" for d in store.drafts())
    for d in store.drafts():
        ready_draft(store, d["id"])
    assert len(make_plan(store, cfg["workflow"], START, 24, 1)["items"]) == 3


def test_cancel_plan_preserves_copy_and_allows_edit(store, cfg, project):
    seeded(store, cfg, project)
    make_plan(store, cfg["workflow"], START, 24, 1)
    with pytest.raises(ValueError, match="Cancel"):
        edit_draft(store, 1, "edit")
    with pytest.raises(ValueError, match="Cancel"):
        generate_drafts(store, cfg["workflow"], refresh=True)
    with pytest.raises(ValueError, match="Cancel"):
        set_order(store, 1, 1)
    assert cancel_plan(store)["cancelled"] == 3
    edit_draft(store, 1, "Yeni metin")
    assert store.drafts()[0]["caption"] == "Yeni metin"


@pytest.mark.parametrize("date", ["2000-01-01T00:00:00+00:00", "2099-01-01T12:00:00"])
def test_past_or_timezone_free_plan_rejected(store, cfg, project, date):
    seeded(store, cfg, project)
    with pytest.raises(ValueError):
        make_plan(store, cfg["workflow"], date, 24, 1)


def test_concurrent_planners_do_not_duplicate(store, cfg, project):
    seeded(store, cfg, project)
    def run(_):
        try:
            return make_plan(store, cfg["workflow"], START, 24, 1)
        except ValueError:
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, range(2)))
    assert sum(r is not None for r in results) == 1
    with store.connect() as c:
        assert c.execute('SELECT count(*) FROM plans').fetchone()[0] == 1


def test_failed_plan_is_atomic(store, cfg, project):
    upsert_projects(store, [project, {**project, "url": project["url"] + "-2"}])
    generate_drafts(store, cfg["workflow"])
    edit_draft(store, 4, "Bekleyen düzenleme")
    with pytest.raises(ValueError):
        make_plan(store, cfg["workflow"], START, 24, 2)
    assert all(d["status"] != "scheduled" for d in store.drafts())


@pytest.mark.parametrize("platform,size", [("instagram",(1080,1350)), ("facebook",(1200,630)), ("linkedin",(1200,1200))])
def test_media_preserves_full_image_with_exact_platform_size(tmp_path, platform, size):
    data = BytesIO()
    Image.new('RGB', (900,300), '#ff0000').save(data, format='PNG')
    path = tmp_path / f'{platform}.jpg'
    render_image(data.getvalue(), path, platform)
    with Image.open(path) as output:
        assert output.size == size
        assert output.getpixel((size[0]//2,size[1]//2))[0] > 240
        corner = output.getpixel((0,0))
        assert corner[1] > 200  # neutral margins: original furniture image was not cropped
