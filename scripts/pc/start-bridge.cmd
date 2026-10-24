@echo off
setlocal
cd /d "%~dp0..\.."
uv run --frozen --extra browser python -m woodmood.bridge serve
