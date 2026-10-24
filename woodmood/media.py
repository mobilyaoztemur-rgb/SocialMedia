from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps

from .settings import PLATFORMS
from .source import Fetcher


def render_image(data, target, platform):
    """Fit the complete furniture image on a neutral canvas without cropping."""
    with Image.open(BytesIO(data)) as original:
        original.seek(0)
        original = ImageOps.exif_transpose(original)
        rgba = original.convert("RGBA")
        flattened = Image.new("RGBA", rgba.size, "#f2eee7")
        flattened.alpha_composite(rgba)
        size = PLATFORMS[platform]["size"]
        fitted = ImageOps.contain(flattened.convert("RGB"), size, Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", size, "#f2eee7")
        canvas.paste(fitted, ((size[0] - fitted.width) // 2, (size[1] - fitted.height) // 2))
        target = Path(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(target, "JPEG", quality=92)
        return {"path": str(target), "width": size[0], "height": size[1]}


def prepare_project_media(store, cfg, project_id, fetcher=None):
    projects = {p["id"]: p for p in store.projects()}
    if project_id not in projects:
        raise ValueError("Project not found")
    p = projects[project_id]
    fetcher = fetcher or Fetcher(cfg["source"]["allowed_hosts"])
    outputs = []
    for index, url in enumerate(p["images"]):
        data = fetcher.get(url, image=True)
        for platform in cfg["workflow"]["platforms"]:
            target = cfg["data_dir"] / "media" / str(project_id) / p["fingerprint"] / f"{index:03}-{platform}.jpg"
            outputs.append({"source": url, "platform": platform, **render_image(data, target, platform)})
    with store.connect() as c:
        store.event(c, "media_prepared", {"project_id": project_id, "files": len(outputs)})
    return outputs
