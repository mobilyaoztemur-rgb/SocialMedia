"""Conservative HTML collector. Never infer project age from list position."""
from datetime import datetime, timezone
import hashlib
import json
from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup
import httpx

from .db import now


class SourceError(ValueError):
    pass


def safe_url(value, base, allowed_hosts):
    url = urlsplit(urljoin(base, value))
    if (url.scheme != "https" or url.hostname not in allowed_hosts or url.username
            or url.password or url.port not in (None, 443)):
        raise SourceError("URL is outside the configured HTTPS source hosts")
    return urlunsplit((url.scheme, url.netloc, url.path or "/", url.query, ""))


class Fetcher:
    def __init__(self, allowed_hosts):
        self.allowed_hosts = allowed_hosts

    def get(self, url, *, image=False):
        for _ in range(6):
            url = safe_url(url, url, self.allowed_hosts)
            # TLS verification remains enabled. Check every redirect before following it.
            with httpx.Client(timeout=30, follow_redirects=False,
                              headers={"User-Agent": "WoodmoodSocial/0.1 (project catalog sync)"}) as client:
                with client.stream("GET", url) as response:
                    if response.is_redirect:
                        url = safe_url(response.headers["location"], url, self.allowed_hosts)
                        continue
                    response.raise_for_status()
                    kind = response.headers.get("content-type", "").lower()
                    if image and not kind.startswith("image/"):
                        raise SourceError("Expected an image response")
                    if not image and not any(t in kind for t in ("text/html", "application/xhtml+xml")):
                        raise SourceError("Expected an HTML response")
                    chunks, count = [], 0
                    limit = 20_000_000 if image else 5_000_000
                    for chunk in response.iter_bytes():
                        count += len(chunk)
                        if count > limit:
                            raise SourceError("Source response exceeds the size limit")
                        chunks.append(chunk)
                    data = b"".join(chunks)
                    return data if image else data.decode(response.encoding or "utf-8")
        raise SourceError("Too many source redirects")


def parse_date(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        # A date without a zone supplies only calendar order, normalized to UTC.
        return dt.replace(tzinfo=dt.tzinfo or timezone.utc).astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError):
        return None


def discover(html, page_url, cfg):
    soup = BeautifulSoup(html, "html.parser")
    urls = []
    for a in soup.select(cfg["project_link_selector"]):
        if not a.get("href"):
            continue
        try:
            url = safe_url(a["href"], page_url, cfg["allowed_hosts"])
        except SourceError:
            continue
        path = urlsplit(url).path
        if any(path.startswith(prefix) and path.rstrip("/") != prefix.rstrip("/")
               for prefix in cfg["project_path_prefixes"]):
            # Project identity ignores marketing query parameters and trailing slashes.
            p = urlsplit(url)
            url = urlunsplit((p.scheme, p.netloc, p.path.rstrip("/"), "", ""))
            if url not in urls:
                urls.append(url)
    next_node = soup.select_one(cfg["next_selector"])
    next_url = (safe_url(next_node["href"], page_url, cfg["allowed_hosts"])
                if next_node and next_node.get("href") else None)
    return urls, next_url


def parse_project(html, url, cfg):
    soup = BeautifulSoup(html, "html.parser")
    title_node = soup.select_one(cfg["title_selector"])
    if not title_node or not title_node.get_text(" ", strip=True):
        raise SourceError("Project title not found; validate source selectors")
    title = title_node.get_text(" ", strip=True)
    description = "\n".join(n.get_text(" ", strip=True)
                             for n in soup.select(cfg["description_selector"]))[:8000]
    images = []
    candidates = []
    for node in soup.select(cfg["image_selector"]):
        value = node.get("data-src") or node.get("src") or node.get("content")
        # Use the largest declared source rather than 900px display thumbnails.
        sources = []
        for src in node.get("srcset", "").split(","):
            parts = src.strip().rsplit(None, 1)
            if len(parts) == 2 and parts[1].endswith("w"):
                try:
                    sources.append((int(parts[1][:-1]), parts[0]))
                except ValueError:
                    pass
        if sources:
            value = max(sources)[1]
        if value:
            candidates.append(value)
    for node in soup.select(cfg.get("image_link_selector", ".detay-galeri a[href]")):
        candidates.append(node["href"])
    for value in candidates:
        try:
            image = safe_url(value, url, cfg["allowed_hosts"])
        except SourceError:
            continue
        if image not in images:
            images.append(image)
    if not images:
        raise SourceError("Project images not found; validate source selectors or media hosts")
    # Use publication metadata only. dateModified is not the original project date.
    date = None
    for node in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(node.string or node.get_text())
            stack = data if isinstance(data, list) else [data]
            while stack:
                item = stack.pop(0)
                if not isinstance(item, dict):
                    continue
                stack.extend(item.get("@graph", []))
                if item.get("datePublished"):
                    date = parse_date(item["datePublished"])
                    if date:
                        break
        except (TypeError, ValueError):
            continue
        if date:
            break
    if not date:
        meta = soup.select_one('meta[property="article:published_time"]')
        date = parse_date(meta.get("content")) if meta else None
    if not date:
        time_node = soup.select_one("article time[datetime], main time[datetime]")
        date = parse_date(time_node.get("datetime")) if time_node else None
    data = {"url": url, "title": title, "description": description,
            "images": images, "published_at": date}
    data["fingerprint"] = hashlib.sha256(
        json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return data


def upsert_projects(store, projects, *, initial_project_order=(), append_new_projects=False):
    stamp = now()
    added = changed = 0
    initial_ranks = {url: rank for rank, url in enumerate(initial_project_order, 1)}
    if len(initial_ranks) != len(initial_project_order):
        raise SourceError("Initial queue contains duplicate projects")
    with store.connect() as c:
        c.execute("BEGIN IMMEDIATE")
        for p in projects:
            old = c.execute("SELECT * FROM projects WHERE url=?", (p["url"],)).fetchone()
            if old and old["manual_order"] is None and p["url"] in initial_ranks:
                c.execute("UPDATE projects SET manual_order=? WHERE id=?",
                          (initial_ranks[p["url"]], old["id"]))
            if old and old["fingerprint"] == p["fingerprint"]:
                continue
            if old:
                c.execute("""UPDATE projects SET title=?,description=?,images=?,published_at=?,
                    fingerprint=?,updated_at=?,needs_review=1 WHERE id=?""",
                          (p["title"], p["description"], json.dumps(p["images"]), p["published_at"],
                           p["fingerprint"], stamp, old["id"]))
                # Existing copy is preserved. Invalidate pending publication on source changes.
                c.execute("UPDATE drafts SET status='draft',scheduled_at=NULL,updated_at=? WHERE project_id=?",
                          (stamp, old["id"]))
                store.event(c, "source_changed", {"project_id": old["id"]})
                changed += 1
            else:
                rank = initial_ranks.get(p["url"])
                if rank is None and append_new_projects:
                    highest = c.execute("SELECT max(manual_order) FROM projects").fetchone()[0] or 0
                    rank = max(highest, len(initial_ranks)) + 1
                c.execute("""INSERT INTO projects(url,title,description,images,published_at,
                    fingerprint,discovered_at,updated_at,manual_order) VALUES(?,?,?,?,?,?,?,?,?)""",
                          (p["url"], p["title"], p["description"], json.dumps(p["images"]),
                           p["published_at"], p["fingerprint"], stamp, stamp, rank))
                added += 1
        store.event(c, "catalog_sync", {"added": added, "changed": changed, "seen": len(projects)})
    return {"added": added, "changed": changed, "seen": len(projects)}


def scan(store, cfg, fetcher=None):
    fetcher = fetcher or Fetcher(cfg["allowed_hosts"])
    with store.connect() as c:
        scan_id = c.execute("INSERT INTO scans(started_at,status) VALUES(?, 'running')", (now(),)).lastrowid
    try:
        page, visited, links = cfg["url"], set(), []
        while page:
            if page in visited:
                raise SourceError("Pagination cycle detected; catalog was not changed")
            if len(visited) >= cfg["max_pages"]:
                raise SourceError("Pagination exceeds max_pages; catalog was not changed")
            visited.add(page)
            found, page = discover(fetcher.get(page), page, cfg)
            links.extend(u for u in found if u not in links)
        if not links:
            raise SourceError("No project links found; validate live HTML and source selectors")
        # All pages must parse before applying changes; a failed fetch cannot erase the catalog.
        projects = [parse_project(fetcher.get(url), url, cfg) for url in links]
        result = upsert_projects(store, projects,
                                 initial_project_order=cfg.get("initial_project_order", ()),
                                 append_new_projects=cfg.get("append_new_projects", False))
        with store.connect() as c:
            c.execute("UPDATE scans SET status='ok',finished_at=?,discovered=? WHERE id=?",
                      (now(), len(projects), scan_id))
        return result
    except Exception as exc:
        with store.connect() as c:
            c.execute("UPDATE scans SET status='failed',finished_at=?,error=? WHERE id=?",
                      (now(), type(exc).__name__ + ": source scan failed; inspect network and selectors", scan_id))
        raise
