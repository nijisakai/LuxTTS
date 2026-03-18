# 单阶段构建
FROM docker.1ms.run/nvidia/cuda:12.8.1-cudnn-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility \
    HF_ENDPOINT=https://hf-mirror.com

# 使用清华 HTTPS 镜像源（绕过代理 HTTP 拦截）
RUN sed -i 's|http://archive.ubuntu.com|https://mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list && \
    sed -i 's|http://security.ubuntu.com|https://mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list && \
    apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-pip python3-dev python3-venv \
        git build-essential libsndfile1 ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
# 升级 pip，安装 uv（独立二进制）
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir uv flask soundfile
# 先装支持 Blackwell (sm_120) 的 PyTorch + torchaudio
RUN uv pip install --system --no-cache torch torchaudio --index-url https://download.pytorch.org/whl/cu128
# 再装其它依赖
RUN uv pip install --system --no-cache -r requirements.txt

# 复制项目代码
COPY . .

# 创建 audio 目录（用于挂载参考音频）
RUN mkdir -p /app/audio

# 构建时预下载模型（运行时完全离线）
RUN python3 -c "\
from huggingface_hub import snapshot_download; \
snapshot_download('YatharthS/LuxTTS'); \
print('LuxTTS model downloaded')"
RUN python3 -c "\
from transformers import pipeline; \
pipeline('automatic-speech-recognition', model='openai/whisper-base'); \
print('Whisper model downloaded')"

# 暴露端口
EXPOSE 9880

# 健康检查（兼容 Docker 和 Podman）
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:9880/health')" || exit 1

# 启动 API 服务
CMD ["python3", "api_server.py"]
