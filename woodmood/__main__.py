import argparse
import json
import time

from .db import Store
from .settings import load_settings
from .source import scan
from .workflow import generate_drafts, make_plan


def main():
    parser = argparse.ArgumentParser(description="Woodmood social automation — simulation only")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    sub.add_parser("scan")
    sub.add_parser("drafts").add_argument("--refresh", action="store_true")
    sub.add_parser("worker")
    server = sub.add_parser("serve")
    server.add_argument("--port", type=int, default=8000)
    plan = sub.add_parser("plan")
    plan.add_argument("--first-at", required=True, help="ISO timestamp including timezone offset")
    plan.add_argument("--interval-hours", required=True, type=int)
    plan.add_argument("--count", type=int, default=1)
    args = parser.parse_args()
    cfg = load_settings()
    store = Store(cfg["data_dir"] / "woodmood.sqlite3")
    if args.command == "serve":
        import uvicorn
        from .app import create_app
        uvicorn.run(create_app(cfg), host="127.0.0.1", port=args.port)
        return
    if args.command == "init":
        result = {"database_initialized": True, "publishing": "simulation_only"}
    elif args.command == "scan":
        result = scan(store, cfg["source"])
        result["drafts"] = generate_drafts(store, cfg["workflow"])
    elif args.command == "drafts":
        result = generate_drafts(store, cfg["workflow"], refresh=args.refresh)
    elif args.command == "plan":
        result = make_plan(store, cfg["workflow"], args.first_at, args.interval_hours, args.count)
    elif args.command == "worker":
        # Run one supervised worker. It scans and prepares copy, never publishes.
        while True:
            try:
                result = scan(store, cfg["source"])
                result["drafts"] = generate_drafts(store, cfg["workflow"])
                print(json.dumps(result), flush=True)
            except Exception as exc:
                # No URL, headers, credential values or remote response bodies in worker logs.
                print(json.dumps({"status": "scan_failed", "error_type": type(exc).__name__}), flush=True)
            time.sleep(cfg["source"]["scan_interval_seconds"])
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
