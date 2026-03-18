# LuxTTS Docker API

基于 [LuxTTS](https://github.com/ysharma3501/LuxTTS) 的 Docker 容器化 API 服务，支持 Docker 和 Podman。

## 构建镜像

- **底层镜像**：`nvidia/cuda:12.8.1-cudnn-devel-ubuntu22.04`
- **GPU 支持**：RTX 4090、RTX 5080 等（PyTorch cu128，覆盖 sm_89 ~ sm_120）
- **模型来源**：构建时自动从 HuggingFace 下载并打包进镜像，运行时完全离线
- **离线运行**：构建完成后不再需要网络连接
- **输出音频**：48kHz WAV

## 前置要求

- NVIDIA GPU
- 已安装 [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
- Docker（含 Docker Compose）或 Podman

## 快速开始

### Docker

```bash
git clone https://github.com/nijisakai/LuxTTS.git
cd LuxTTS

# 将参考音频放入 audio/ 目录（项目已包含示例音频）
# cp /path/to/your_reference.wav audio/

# 构建并启动
docker compose build && docker compose up -d

# 查看日志（首次启动需下载模型，约需几分钟）
docker logs -f luxtts-api
```

### Podman

```bash
git clone https://github.com/nijisakai/LuxTTS.git
cd LuxTTS

bash podman-run.sh
```

## 注意事项

1. **构建需要网络**：构建阶段会下载约 1.4GB 模型文件（LuxTTS + Whisper），全部打包进镜像，构建完成后运行完全离线
2. **参考音频要求**：至少 3 秒，支持 wav/mp3 格式，放入 `audio/` 目录即可
3. **网络问题**：如果构建时遇到 apt 源连接失败，Dockerfile 已配置清华 HTTPS 镜像源；HuggingFace 下载慢可在 Dockerfile 中添加 `ENV HF_ENDPOINT=https://hf-mirror.com`
4. **显存占用**：约 1GB VRAM，几乎所有独立 GPU 都能运行
5. **Podman SELinux**：volume 挂载已使用 `:z` 标记，`podman-run.sh` 已添加 `--security-opt=label=disable`

## API 接口

**服务地址**：`http://localhost:9880`

### 合成语音

```
GET  http://localhost:9880/?text=要合成的文本&speaker=audio/参考音频.wav
POST http://localhost:9880/  (支持 form 和 JSON body)
```

| 参数 | 必填 | 说明 |
|------|------|------|
| `text` | 是 | 待合成文本 |
| `speaker` | 是 | 参考音频路径（相对于项目根目录） |

**返回**：WAV 音频流（48kHz）

### 使用示例

**浏览器直接访问：**
```
http://localhost:9880/?text=你好,测试一下&speaker=audio/花魁.wav
```

**curl 命令：**
```bash
# GET 请求
curl "http://localhost:9880/?text=你好世界&speaker=audio/花魁.wav" -o output.wav

# POST JSON
curl -X POST http://localhost:9880/ \
  -H "Content-Type: application/json" \
  -d '{"text": "你好世界", "speaker": "audio/花魁.wav"}' \
  -o output.wav
```

### 健康检查

```bash
curl http://localhost:9880/health
# 返回: {"status": "ok", "device": "cuda"}
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
| `DEVICE` | `cuda` | 运行设备（`cuda` 或 `cpu`） |
| `PORT` | `9880` | 服务端口 |
| `NUM_STEPS` | `4` | 采样步数（3-4 为最佳效率） |
| `GUIDANCE_SCALE` | `3.0` | 引导尺度 |
| `T_SHIFT` | `0.5` | 采样温度（越高质量越好但可能有发音错误） |
| `SPEED` | `1.0` | 语速（1.0=正常，>1.0=加速） |
| `RMS` | `0.01` | 音量控制（越大越响） |
| `REF_DURATION` | `5` | 参考音频最大时长（秒） |
| `THREADS` | `4` | CPU 线程数（仅 `DEVICE=cpu` 时生效） |

## 管理命令

```bash
# 查看日志
docker logs -f luxtts-api

# 停止服务
docker compose down

# 重建并重启
docker compose build && docker compose up -d

# Podman 查看日志
podman logs -f luxtts-api
```

## 镜像迁移（离线部署到其他机器）

构建完成后，可以将镜像导出到其他机器直接使用，无需网络。

### 导出镜像（当前机器）

```bash
# Docker 导出
docker save luxtts-luxtts | gzip > luxtts-image.tar.gz

# Podman 导出
podman save luxtts-api | gzip > luxtts-image.tar.gz
```

### 导入镜像（目标机器）

```bash
# Docker 导入
docker load < luxtts-image.tar.gz
cd LuxTTS
docker compose up -d

# Podman 导入
podman load < luxtts-image.tar.gz
cd LuxTTS
bash podman-run.sh
```

> Docker 和 Podman 镜像格式互相兼容，`docker save` 导出的可以用 `podman load` 导入，反之亦然。

## 致谢

- [LuxTTS](https://github.com/ysharma3501/LuxTTS) — 原始项目
- [ZipVoice](https://github.com/k2-fsa/ZipVoice) — 模型架构
- [Vocos](https://github.com/gemelo-ai/vocos.git) — 声码器
