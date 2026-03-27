# Intel XGPU 服务器测试指南

本文档提供在 Intel Arc GPU（XPU）服务器上完整部署和测试 LuxTTS 的步骤。

---

## 一、必要前提条件

### 硬件要求
- Intel Arc 独立显卡（A380 / A750 / A770 / B580 等）或搭载 Xe 核显的 Intel 处理器
- 内存：≥ 16 GB RAM（模型约占用 2 GB + 系统）
- 存储：≥ 20 GB 可用空间（镜像约 10 GB，模型约 2 GB）

### 系统要求
- **操作系统**：Ubuntu 22.04 LTS 或 Ubuntu 24.04 LTS（推荐）
- **内核**：≥ 6.2（带 `xe` 驱动）或 ≥ 5.15（带 `i915` 驱动）

### 软件要求

#### 1. Intel GPU 用户态驱动（宿主机必装）
```bash
# Ubuntu 22.04 / 24.04
sudo apt-get update
sudo apt-get install -y \
    intel-opencl-icd \
    intel-level-zero-gpu \
    level-zero \
    intel-media-va-driver-non-free \
    libmfx1 libmfxgen1 libvpl2 \
    libegl-mesa0 libegl1-mesa \
    libgles2-mesa libgl1-mesa-dri \
    libgbm1 libdrm2
```

验证驱动安装：
```bash
ls /dev/dri/
# 应能看到 card0、renderD128 等设备节点
```

#### 2. Docker（推荐）或 Podman
```bash
# 安装 Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# 重新登录使 group 生效

# 验证
docker --version
```

#### 3. 网络要求
- 构建镜像时需要下载约 **3 GB** 数据（PyTorch + 模型）
- 已配置清华镜像源（pip）和 hf-mirror.com（HuggingFace），国内环境可正常使用

---

## 二、快速开始

### 步骤 1：克隆仓库

```bash
git clone https://github.com/nijisakai/LuxTTS.git
cd LuxTTS
```

### 步骤 2：环境诊断（强烈推荐）

在服务器上先运行诊断脚本，确认硬件和驱动就绪：

```bash
# 安装最小依赖（仅诊断用）
pip3 install torch intel-extension-for-pytorch onnxruntime 2>/dev/null

python3 check_xpu.py
```

正常输出示例：
```
============================================================
  2. PyTorch
============================================================
  ✅ OK     PyTorch 已安装  (版本: 2.5.0)
  ✅ OK     torch.xpu.is_available() [PyTorch >= 2.4 原生 XPU]

============================================================
  3. Intel Extension for PyTorch (IPEX)
============================================================
  ✅ OK     IPEX 已安装  (版本: 2.5.10)
  ✅ OK     ipex.xpu.is_available()  (1 个 XPU 设备)
  ✅ OK     XPU[0]: Intel(R) Arc(TM) A770 Graphics
           显存: 16376 MB
```

### 步骤 3：构建 Intel GPU 镜像

```bash
# 构建（约需 10-20 分钟，含模型下载）
docker compose -f docker-compose.intel.yml build

# 查看构建日志中的关键信息
# 应出现 "LuxTTS model downloaded" 和 "Whisper model downloaded"
```

### 步骤 4：启动服务

```bash
docker compose -f docker-compose.intel.yml up -d

# 查看启动日志（等待出现 "模型加载完成"）
docker logs -f luxtts-intel
```

正常启动日志：
```
2026-xx-xx [INFO] 正在加载 LuxTTS 模型 (device=xpu) ...
Loading model on GPU (device=xpu)
2026-xx-xx [INFO] 模型加载完成
 * Running on http://0.0.0.0:9880
```

### 步骤 5：测试合成

```bash
# 健康检查（确认 XPU 已激活）
curl http://localhost:9880/health
# 期望返回: {"device": "xpu", "npu_available": false, "status": "ok", "xpu_available": true}

# 基础合成测试
curl "http://localhost:9880/?text=你好，这是一个测试&speaker=audio/花魁.wav" \
  -o test_output.wav

# 验证输出文件
ls -lh test_output.wav          # 应有大小（几十 KB 以上）
file test_output.wav            # 应为 RIFF (little-endian) data, WAVE audio
```

---

## 三、Podman 用户

```bash
# 使用 Podman 启动
bash podman-run-intel.sh

# 或手动运行
podman build -t luxtts-intel -f Dockerfile.intel .
podman run -d \
    --name luxtts-intel \
    -p 9880:9880 \
    -v ./audio:/app/audio:z \
    -e DEVICE=xpu \
    --device /dev/dri \
    --group-add video \
    --group-add render \
    --security-opt=label=disable \
    luxtts-intel
```

---

## 四、完整参数测试

```bash
# 全参数 GET 请求
curl "http://localhost:9880/?text=今天天气真好，我们一起去散步吧&speaker=audio/花魁.wav\
&num_steps=4&guidance_scale=3.0&t_shift=0.9&speed=1.0&rms=0.01\
&ref_duration=5&return_smooth=false" \
  -o output_full.wav

# POST JSON 请求
curl -X POST http://localhost:9880/ \
  -H "Content-Type: application/json" \
  -d '{
    "text": "欢迎使用 LuxTTS 语音合成系统",
    "speaker": "audio/花魁.wav",
    "num_steps": 4,
    "guidance_scale": 3.0,
    "t_shift": 0.9,
    "speed": 1.0,
    "rms": 0.01,
    "ref_duration": 5,
    "return_smooth": false
  }' \
  -o output_post.wav
```

---

## 五、性能调优

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| `num_steps` | 3 或 4 | 3 更快，4 质量更好 |
| `t_shift` | 0.7–0.9 | 提高发音清晰度（越高可能有错音） |
| `ref_duration` | 3–5 | 参考音频时长，5 秒通常最佳 |
| `return_smooth` | `false` | XPU 上通常不需要，出现金属音再开启 |

---

## 六、常见问题排查

### 问题 1：`/dev/dri` 不存在
```bash
# 检查内核驱动是否加载
lsmod | grep -E "i915|xe"

# 若未加载
sudo modprobe i915    # 老款 Arc（A 系列）
sudo modprobe xe      # 新款 Arc（Battlemage）
```

### 问题 2：容器内无法访问 GPU
```bash
# 检查 render 用户组是否存在
getent group render
getent group video

# 宿主机添加用户到 render 组
sudo usermod -aG render,video $USER
# 重新登录后生效
```

### 问题 3：IPEX 未找到 XPU 设备
```bash
# 在容器内验证
docker exec -it luxtts-intel python3 -c \
  "import intel_extension_for_pytorch as ipex; print(ipex.xpu.is_available())"

# 若返回 False，检查设备节点传入
docker inspect luxtts-intel | grep -A5 Devices
```

### 问题 4：合成结果为空 / 无声
- 确认 `speaker` 参数指向的 WAV 文件存在且时长 ≥ 3 秒
- 尝试增大 `ref_duration`（如设为 `1000` 使用全段）
- 尝试开启 `return_smooth=true`

### 问题 5：构建时 HuggingFace 下载失败
```bash
# 方法一：使用镜像（已内置）
# Dockerfile.intel 已设置 HF_ENDPOINT=https://hf-mirror.com

# 方法二：手动预下载后放入缓存
HF_ENDPOINT=https://hf-mirror.com \
python3 -c "from huggingface_hub import snapshot_download; snapshot_download('YatharthS/LuxTTS')"
```

---

## 七、管理命令

```bash
docker logs -f luxtts-intel          # 实时日志
docker compose -f docker-compose.intel.yml down     # 停止服务
docker compose -f docker-compose.intel.yml restart  # 重启
docker exec -it luxtts-intel python3 check_xpu.py   # 容器内诊断
```

---

## 八、离线部署（无网络环境）

```bash
# 有网机器：导出镜像
docker save luxtts-intel | gzip > luxtts-intel.tar.gz

# 目标机器：导入并启动
docker load < luxtts-intel.tar.gz
git clone https://github.com/nijisakai/LuxTTS.git
cd LuxTTS
docker compose -f docker-compose.intel.yml up -d
```
