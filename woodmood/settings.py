import os
from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parent.parent
PLATFORMS = {
    "instagram": {"label": "Instagram", "size": (1080, 1350), "limit": 2200},
    "facebook": {"label": "Facebook", "size": (1200, 630), "limit": 5000},
    "linkedin": {"label": "LinkedIn", "size": (1200, 1200), "limit": 3000},
}


def load_settings():
    path = Path(os.environ.get("WOODMOOD_CONFIG", ROOT / "config.toml"))
    with path.open("rb") as f:
        cfg = tomllib.load(f)
    if cfg["workflow"]["publishing_enabled"]:
        raise ValueError("Live publishing is not implemented; publishing_enabled must be false")
    if cfg["workflow"]["mode"] not in {"automatic", "review"}:
        raise ValueError("Unknown workflow mode")
    if not cfg["workflow"]["platforms"] or set(cfg["workflow"]["platforms"]) - PLATFORMS.keys():
        raise ValueError("Unsupported platforms")
    if cfg["source"]["scan_interval_seconds"] < 60:
        raise ValueError("Scan interval must be at least 60 seconds")
    with (ROOT / "accounts.toml").open("rb") as f:
        cfg["accounts"] = tomllib.load(f)["accounts"]
    cfg["data_dir"] = Path(os.environ.get("WOODMOOD_DATA_DIR", ROOT / "var")).resolve()
    return cfg
