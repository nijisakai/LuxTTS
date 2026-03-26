# Dockerfile.arc — Intel Arc GPU (XPU) 版本
# 基于 Intel Extension for PyTorch (IPEX) XPU 镜像
FROM intel/intel-extension-for-pytorch:2.7.10-xpu-pip-base

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_ENDPOINT=https://hf-mirror.com

# 使用清华 HTTPS 镜像源
RUN sed -i 's|http://archive.ubuntu.com|https://mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list && \
    sed -i 's|http://security.ubuntu.com|https://mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list && \
    apt-get update && apt-get install -y --no-install-recommends \
        python3-pip python3-dev \
        git build-essential libsndfile1 ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# 升级 pip，安装基础依赖
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir uv flask soundfile

# 安装其它依赖（基础镜像已包含 PyTorch + IPEX XPU，跳过 torch/torchaudio）
RUN uv pip install --system --no-cache -r requirements.txt --no-deps torch torchaudio

# 复制项目代码
COPY . .

# 创建 audio 目录
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

EXPOSE 9880

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:9880/health')" || exit 1

CMD ["python3", "api_server.py"]
