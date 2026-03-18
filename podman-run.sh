#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# podman-run.sh — 使用 Podman + NVIDIA GPU 启动 LuxTTS API
# 用法: bash podman-run.sh
# ──────────────────────────────────────────────────────────────
set -euo pipefail

IMAGE_NAME="luxtts-api"
CONTAINER_NAME="luxtts-api"
PORT="${PORT:-9880}"
AUDIO_DIR="$(cd "$(dirname "$0")" && pwd)/audio"

# 构建镜像
echo ">>> 构建镜像 ${IMAGE_NAME} ..."
podman build -t "${IMAGE_NAME}" .

# 停止并删除旧容器（如果存在）
if podman container exists "${CONTAINER_NAME}" 2>/dev/null; then
    echo ">>> 停止旧容器 ..."
    podman stop "${CONTAINER_NAME}" || true
    podman rm "${CONTAINER_NAME}" || true
fi

# 启动容器
echo ">>> 启动容器 ..."
podman run -d \
    --name "${CONTAINER_NAME}" \
    --replace \
    -p "${PORT}:9880" \
    -v "${AUDIO_DIR}:/app/audio:z" \
    -e DEVICE=cuda \
    -e PORT=9880 \
    -e NUM_STEPS=4 \
    -e GUIDANCE_SCALE=3.0 \
    -e T_SHIFT=0.5 \
    -e SPEED=1.0 \
    -e RMS=0.01 \
    -e REF_DURATION=5 \
    -e THREADS=4 \
    -e NVIDIA_VISIBLE_DEVICES=all \
    --device nvidia.com/gpu=all \
    --security-opt=label=disable \
    "${IMAGE_NAME}"

echo ">>> LuxTTS API 已启动: http://localhost:${PORT}/"
echo ">>> 健康检查: http://localhost:${PORT}/health"
echo ">>> 查看日志: podman logs -f ${CONTAINER_NAME}"
