#!/bin/sh
# Vercel Build Command: sh build.sh  (Output Directory: .)
# 환경변수 API_BASE_URL 을 config.js 로 주입한다.
set -e
if [ -z "$API_BASE_URL" ]; then
  echo "API_BASE_URL 환경변수가 필요합니다." >&2
  exit 1
fi
echo "window.API_BASE_URL = \"$API_BASE_URL\";" > config.js
