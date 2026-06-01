#!/bin/bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend"
BACKEND_DIR="$ROOT_DIR/backend"

echo "=== Kitsu Publisher Build Script ==="

# 1. 프론트엔드 빌드
echo ""
echo "[1/2] 프론트엔드 빌드 중..."
cd "$FRONTEND_DIR"
bun install
bun run build
echo "프론트엔드 빌드 완료."

# 2. PyInstaller 빌드
echo ""
echo "[2/2] 앱 패키징 중 (PyInstaller)..."
cd "$BACKEND_DIR"
uv run pyinstaller KitsuPublisher.spec --noconfirm

echo ""
echo "=== 빌드 완료 ==="
echo "결과물: $BACKEND_DIR/dist/"
ls "$BACKEND_DIR/dist/"
