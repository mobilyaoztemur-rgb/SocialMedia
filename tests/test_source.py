from pathlib import Path
import pytest
from woodmood.source import SourceError, discover, parse_project, safe_url, scan, upsert_projects

FIXTURES = Path(__file__).parent / "fixtures"


def test_discovery_deduplicates_and_rejects_external_hosts(cfg):
    links, next_url = discover((FIXTURES / "catalog.html").read_text(), cfg["source"]["url"], cfg["source"])
    assert links == ["https://woodmoodmobilya.com/tr/projeler/ornek-a", "https://woodmoodmobilya.com/tr/projeler/ornek-b"]
    assert next_url is None


def test_project_extracts_publication_date_images_and_source_copy(project):
    assert project["published_at"] == "2021-05-06T00:00:00+00:00"
    assert len(project["images"]) == 2
    assert project["title"] == "Örnek Proje A — Test Verisi"
    assert "örnek proje açıklaması" in project["description"]


def test_modified_date_does_not_become_original_date(cfg):
    html = (FIXTURES / "project.html").read_text().replace('"datePublished"', '"dateModified"')
    assert parse_project(html, cfg["source"]["url"], cfg["source"])["published_at"] is None


@pytest.mark.parametrize("url", ["http://woodmoodmobilya.com/x", "https://evil.example/x", "https://u:p@woodmoodmobilya.com/x", "https://woodmoodmobilya.com:8443/x", "file:///etc/passwd"])
def test_source_url_boundary(url, cfg):
    with pytest.raises(SourceError):
        safe_url(url, cfg["source"]["url"], cfg["source"]["allowed_hosts"])


def test_upsert_is_repeatable_and_does_not_delete_missing_projects(store, project):
    assert upsert_projects(store, [project])["added"] == 1
    assert upsert_projects(store, [project]) == {"added": 0, "changed": 0, "seen": 1}
    upsert_projects(store, [])
    assert len(store.projects()) == 1


def test_scan_failure_does_not_partially_update_catalog(store, cfg, project):
    upsert_projects(store, [project])
    class FailingSource:
        def get(self, url):
            if url == cfg["source"]["url"]:
                return (FIXTURES / "catalog.html").read_text()
            if url.endswith('ornek-a'):
                return (FIXTURES / "project.html").read_text().replace('Test Verisi', 'Changed')
            raise OSError("offline")
    with pytest.raises(OSError):
        scan(store, cfg["source"], FailingSource())
    assert store.projects()[0]["fingerprint"] == project["fingerprint"]
    assert store.latest_scan()["status"] == "failed"


def test_paginated_scan_success(store, cfg):
    class Source:
        def get(self, url):
            if url == cfg["source"]["url"]:
                return '<a class="kart-link" href="/tr/projeler/ornek-a">A</a><a rel="next" href="?page=2">Next</a>'
            if url.endswith('?page=2'):
                return '<a class="kart-link" href="/tr/projeler/ornek-b">B</a>'
            return (FIXTURES / "project.html").read_text()
    assert scan(store, cfg["source"], Source())["added"] == 2
    assert store.latest_scan()["discovered"] == 2


def test_no_project_links_is_failure_not_empty_success(store, cfg):
    class Empty:
        def get(self, url):
            return '<html><body>Access denied</body></html>'
    with pytest.raises(SourceError, match="No project links"):
        scan(store, cfg["source"], Empty())
    assert store.latest_scan()["status"] == "failed"


def test_redirect_to_foreign_host_is_not_followed(cfg, monkeypatch):
    import httpx
    from woodmood.source import Fetcher
    requests = []
    def response(request):
        requests.append(str(request.url))
        return httpx.Response(302, headers={"location": "https://evil.example/"})
    original_client = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: original_client(transport=httpx.MockTransport(response), **kwargs))
    with pytest.raises(SourceError):
        Fetcher(cfg["source"]["allowed_hosts"]).get(cfg["source"]["url"])
    assert len(requests) == 1


def test_live_layout_excludes_related_projects_and_uses_original_images(cfg):
    # Minimal regression structure based on inspected live markup, not a fake live fetch.
    html = '''<main><section class="detay-acilis"><h1>Proje</h1>
      <p class="acilis-aciklama">Açıklama</p>
      <img src="/a-900.webp" srcset="/a-400.webp 400w, /a-900.webp 900w, /a.webp 1800w">
      </section><section class="detay-govde"><div class="metin"><p>Proje detayları</p></div></section>
      <div class="detay-galeri"><a href="/a.webp"><img src="/a-900.webp"></a>
      <a href="/b.webp"><img src="/b-900.webp"></a></div>
      <section class="digerleri"><article><p>Başka projenin açıklaması</p><img src="/unrelated.webp"></article></section></main>'''
    p = parse_project(html, cfg["source"]["url"], cfg["source"])
    assert p["images"] == ['https://woodmoodmobilya.com/a.webp', 'https://woodmoodmobilya.com/b.webp']
    assert 'Başka' not in p['description']
    assert 'Proje detayları' in p['description']


def test_owner_order_survives_rescans_and_new_projects_append(store, project):
    # Discover the newest initial project first, and a new project before the remaining backlog.
    urls = [project['url'] + suffix for suffix in ('-oldest', '-second', '-third', '-fourth')]
    projects = [{**project, 'url': url} for url in urls]
    options = {'initial_project_order': urls, 'append_new_projects': True}
    upsert_projects(store, [projects[3]], **options)
    new = {**project, 'url': project['url'] + '-new'}
    upsert_projects(store, [new, projects[2], projects[0], projects[1]], **options)
    assert [p['url'] for p in store.projects()] == urls + [new['url']]
    assert [p['manual_order'] for p in store.projects()] == [1, 2, 3, 4, 5]
    assert upsert_projects(store, [new] + projects[::-1], **options)['added'] == 0
    assert [p['url'] for p in store.projects()] == urls + [new['url']]


def test_initial_owner_order_applies_to_preexisting_catalog(store, project):
    upsert_projects(store, [project])
    assert store.projects()[0]['manual_order'] is None
    upsert_projects(store, [project], initial_project_order=[project['url']], append_new_projects=True)
    assert store.projects()[0]['manual_order'] == 1
