# LuxTTS Docker API

基于 [LuxTTS](https://github.com/ysharma3501/LuxTTS) 的 Docker 容器化 API 服务，支持 Docker 和 Podman。

## 特性

- **NVIDIA GPU 加速**：PyTorch CUDA (cu128)，支持 RTX 4090/5080 等
- **Intel Arc GPU 加速**：PyTorch XPU (IPEX)，支持 Arc A770/B580 等
- **离线运行**：模型构建时打包进镜像，运行时完全离线
- **输出音频**：48kHz WAV
- **显存占用**：约 1GB VRAM

## 前置要求

### NVIDIA GPU
- NVIDIA GPU
- 已安装 [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
- Docker（含 Docker Compose）或 Podman

### Intel Arc GPU
- Intel Arc GPU（A 系列或 B 系列）
- 已安装 [Intel GPU 驱动](https://dgpu-docs.intel.com/driver/installation.html)
- Docker（含 Docker Compose）

## 快速开始

### NVIDIA GPU（Docker）

```bash
git clone https://github.com/nijisakai/LuxTTS.git
cd LuxTTS

# 将参考音频放入 audio/ 目录（项目已包含示例音频）
# cp /path/to/your_reference.wav audio/

# 构建并启动
docker compose build && docker compose up -d

# 查看日志
docker logs -f luxtts-gpu
```

### NVIDIA GPU（Podman）

```bash
git clone https://github.com/nijisakai/LuxTTS.git
cd LuxTTS
bash podman-run.sh
```

### Intel Arc GPU（Docker）

```bash
git clone https://github.com/nijisakai/LuxTTS.git
cd LuxTTS

# 构建并启动（使用 Intel Arc 专用 Compose 文件）
docker compose -f docker-compose-arc.yml build
docker compose -f docker-compose-arc.yml up -d

# 查看日志
docker logs -f luxtts-arc
```

启动后访问：`http://localhost:9880/?text=你好&speaker=audio/花魁.wav`

## API 接口

**服务地址**：`http://localhost:9880`

### 合成语音

```
GET  http://localhost:9880/?text=要合成的文本&speaker=audio/参考音频.wav
POST http://localhost:9880/  (支持 form 和 JSON body)
```

### 参数说明

| 参数 | 必填 | 类型 | 默认值 | 说明 |
|------|------|------|--------|------|
| `text` | 是 | string | — | 待合成文本 |
| `speaker` | 是 | string | — | 参考音频路径（相对于项目根目录） |
| `num_steps` | 否 | int | `4` | 采样步数，值越大质量越好但更慢（推荐 3-4） |
| `guidance_scale` | 否 | float | `3.0` | 引导尺度，控制与参考音色的相似度 |
| `t_shift` | 否 | float | `0.5` | 采样温度，越高质量越好但可能有发音错误 |
| `speed` | 否 | float | `1.0` | 语速控制（1.0=正常，>1.0=加速，<1.0=减速） |
| `rms` | 否 | float | `0.01` | 音量控制，越大越响（推荐 0.01） |
| `ref_duration` | 否 | int | `5` | 参考音频最大时长（秒），降低可加速推理，如有瑕疵可设为 1000 |
| `return_smooth` | 否 | bool | `false` | 平滑模式，听到金属音时可设为 true |

> 所有可选参数不传时使用环境变量默认值（见下方环境变量表）。

**返回**：WAV 音频流（48kHz）

### 使用示例

**浏览器直接访问：**
```
http://localhost:9880/?text=你好,测试一下&speaker=audio/花魁.wav
```

**GET 全参数示例：**
```
http://localhost:9880/?text=你好世界&speaker=audio/花魁.wav&num_steps=4&guidance_scale=3.0&t_shift=0.9&speed=1.0&rms=0.01&ref_duration=5&return_smooth=false
```

**curl（GET）：**
```bash
curl "http://localhost:9880/?text=你好世界&speaker=audio/花魁.wav" -o output.wav
```

**curl（POST JSON 全参数）：**
```bash
curl -X POST http://localhost:9880/ \
  -H "Content-Type: application/json" \
  -d '{
    "text": "你好世界",
    "speaker": "audio/花魁.wav",
    "num_steps": 4,
    "guidance_scale": 3.0,
    "t_shift": 0.9,
    "speed": 1.0,
    "rms": 0.01,
    "ref_duration": 5,
    "return_smooth": false
  }' \
  -o output.wav
```

**PowerShell：**
```powershell
Invoke-WebRequest "http://localhost:9880/?text=你好世界&speaker=audio/花魁.wav&speed=1.2&t_shift=0.9" -OutFile output.wav
```

### 健康检查

```bash
curl http://localhost:9880/health
# NVIDIA GPU 返回: {"status": "ok", "device": "cuda"}
# Intel Arc 返回:  {"status": "ok", "device": "xpu"}
```

## 示例音频

项目 `audio/` 目录已包含以下参考音色：

| 文件 | 音色 |
|------|------|
| `audio/花魁.wav` | 花魁 |
| `audio/厨娘.wav` | 厨娘 |
| `audio/大叔.wav` | 大叔 |
| `audio/付雅雯.wav` | 付雅雯 |
| `audio/龚晓.wav` | 龚晓 |

## 环境变量

可在 `docker-compose.yml` 或启动命令中修改：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEVICE` | 自动检测（cuda > xpu > cpu） | 运行设备（`cuda`=NVIDIA，`xpu`=Intel Arc，`cpu`=纯 CPU） |
| `PORT` | `9880` | 服务端口 |
| `NUM_STEPS` | `4` | 采样步数（3-4 为最佳效率） |
| `GUIDANCE_SCALE` | `3.0` | 引导尺度 |
| `T_SHIFT` | `0.5` | 采样温度（越高质量越好但可能有发音错误） |
| `SPEED` | `1.0` | 语速（1.0=正常，>1.0=加速） |
| `RMS` | `0.01` | 音量控制（越大越响） |
| `REF_DURATION` | `5` | 参考音频最大时长（秒） |
| `THREADS` | `4` | CPU 线程数 |

## 管理命令

```bash
# NVIDIA GPU
docker logs -f luxtts-gpu           # 查看日志
docker compose down                  # 停止
docker compose build && docker compose up -d  # 重新构建并启动

# Intel Arc GPU
docker logs -f luxtts-arc           # 查看日志
docker compose -f docker-compose-arc.yml down
docker compose -f docker-compose-arc.yml build && docker compose -f docker-compose-arc.yml up -d

# Podman（NVIDIA）
podman logs -f luxtts-gpu
```

## 镜像迁移（离线部署）

```bash
# 导出
docker save luxtts-gpu | gzip > luxtts-gpu.tar.gz

# 导入（目标机器）
docker load < luxtts-gpu.tar.gz
cd LuxTTS && docker compose up -d
```

> Docker 和 Podman 镜像格式互相兼容。

## 注意事项

1. **构建需要网络**：构建阶段会下载约 1.4GB 模型文件（LuxTTS + Whisper），全部打包进镜像
2. **参考音频要求**：至少 3 秒，支持 wav/mp3 格式，放入 `audio/` 目录即可
3. **网络问题**：Dockerfile 已配置清华 HTTPS 镜像源；HuggingFace 已默认使用国内镜像（`HF_ENDPOINT=https://hf-mirror.com`）
4. **Podman SELinux**：volume 挂载已使用 `:z` 标记
5. **Intel Arc 驱动**：运行 Intel Arc 版本前需安装 Linux 下的 [Intel GPU 驱动](https://dgpu-docs.intel.com/driver/installation.html)，并确认 `/dev/dri` 设备存在

## 致谢

- [LuxTTS](https://github.com/ysharma3501/LuxTTS) — 原始项目
- [ZipVoice](https://github.com/k2-fsa/ZipVoice) — 模型架构
- [Vocos](https://github.com/gemelo-ai/vocos.git) — 声码器
