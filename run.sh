#!/bin/bash
# 启动本地教学平台（gunicorn，5 worker × 8 thread），日志写入 gunicorn_run.log
cd "$(dirname "$0")" || exit 1
nohup .venv-hermes/bin/gunicorn -c gunicorn_conf.py app:app >> gunicorn_run.log 2>&1 < /dev/null &
echo "gunicorn started pid=$!"