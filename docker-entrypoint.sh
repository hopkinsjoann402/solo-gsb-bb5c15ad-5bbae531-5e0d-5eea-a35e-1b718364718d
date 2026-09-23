#!/bin/sh
# 容器一键启动: 初始化(打印配置)并拉起 uvicorn。
set -e

echo "[booklet-imposition] starting uvicorn on ${HOST:-0.0.0.0}:${PORT:-8000}"
echo "[booklet-imposition] MAX_TOTAL_PAGES=${MAX_TOTAL_PAGES:-100000}"

exec uvicorn app.main:app --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}"
