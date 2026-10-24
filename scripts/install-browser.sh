#!/usr/bin/env bash
set -euo pipefail
export UV_TOOL_DIR=/workspace/.tools/uv
export UV_TOOL_BIN_DIR=/workspace/.tools/bin
export UV_CACHE_DIR=/workspace/.cache/uv
uv tool install browser-act-cli==1.4.5 --python 3.12
command -v chromium >/dev/null
command -v certutil >/dev/null
mkdir -p /workspace/.local/share/browseract /workspace/.config/chromium
chmod 700 /workspace/.local/share/browseract /workspace/.config/chromium
