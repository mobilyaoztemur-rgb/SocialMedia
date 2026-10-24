# Development guide

Use the existing `/workspace/SocialMedia` checkout. Each cloud task is isolated; do not create a Git worktree unless the user requests one.

Read README.md and docs/ROADMAP.md before expanding the workflow. The owner selected automatic publishing, with cadence undecided. Instagram, Facebook and LinkedIn have first priority; all nine public account URLs are in accounts.toml.

Install with `uv sync --frozen`, initialize with `uv run --frozen python -m woodmood init`, run checks with `uv run --frozen pytest -q`. Start the local app with `uv run --frozen python -m woodmood serve`. A separate `uv run --frozen python -m woodmood worker` performs periodic source scans, not social publishing. Use one scan worker.

Never represent a simulation as a successful publication. Real network publishing is not implemented yet. Keep source data, generated media, sessions and secrets out of Git; var/ and .env are ignored. Preserve TLS verification. Do not infer project chronology from page order. Keep platform outcomes independent when implementing the next phase, and reconcile ambiguous API timeouts before retrying an external publish.

Tests use synthetic fixtures. The production app must not fall back to fixtures when a real source fetch fails.

Legacy BrowserAct route only (not the current PC bridge): read docs/BROWSER.md and the BrowserAct skill before using BrowserAct operations. Public browser references are in browser.toml; profiles live outside the checkout. The current phase is owner login pending. The owner handles passwords and MFA through remote-assist. After providing a remote-assist control link, do not inspect or operate the session until the owner replies. Never print auth poll keys or export cookies. API integration is an optional later route, not a prerequisite for the selected browser workflow.

The confirmed queue is Azerbaijan, Firat Serhat Motors, Mormenekse, Northernland, then new discoveries appended. It is configured in config.toml; do not ask for those initial dates again. Publishing cadence is still undecided.

Current connection choice supersedes the BrowserAct deployment path: the owner will supply an always-on Windows 10/11 PC and has no Cloudflare-managed domain yet. Read docs/WINDOWS_SETUP.md. The self-hosted Playwright control service is woodmood.bridge, with an authenticated HTTPS client in woodmood.remote. Source helpers are scripts/pc/*.cmd; profiles and token files are outside Git under the Windows user's LocalAppData. BrowserAct remains available as a legacy tool but is not a dependency of the PC bridge.

The owner signs in LOCALLY in the bridge's dedicated visible Chrome. Owner mode is controlled by a private file on that PC, not by an API endpoint. While owner_paused is true, do not inspect screenshots/DOM or perform actions. Only the owner releases it locally via agent-ready.cmd. The remote client uses the currently available shell tool; placing an MCP config in Git does not register a tool in this chat.

Run `uv sync --frozen --extra browser` and `uv run --frozen --extra browser pytest -q` for the full suite. Browser tests use actual Chrome/Chromium with synthetic fixtures; on CI WOODMOOD_TEST_CHROME selects the installed executable. On this isolated cloud host, headless validation explicitly disables the Chromium sandbox; the Windows production config keeps it enabled. Never disable TLS verification. Windows launch scripts and the real Cloudflare/PC route have not yet been executed on the owner's computer.

For this cloud runtime's remote-client credential file, set XDG_DATA_HOME=/workspace/.local/share before `python -m woodmood.remote configure`. The URL is non-secret; the bridge token and optional Cloudflare Access fields are secret. Do not echo them or put them in CLI arguments. Quick Tunnel has no Access SSO by default; every bridge endpoint requires its bearer token. No real PC endpoint or token is connected yet. No publishing occurs during account setup; cadence remains undecided.
