#!/usr/bin/env python3
"""
XPU/NPU 环境诊断脚本
在 Intel XGPU 服务器上运行此脚本以验证环境是否就绪

用法:
    python3 check_xpu.py
"""

import sys
import subprocess


def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def check(label, ok, detail=""):
    status = "✅ OK    " if ok else "❌ FAILED"
    msg = f"  {status}  {label}"
    if detail:
        msg += f"\n           {detail}"
    print(msg)
    return ok


# ── 1. Python 版本 ──────────────────────────────────────────────
section("1. Python 环境")
py_ok = sys.version_info >= (3, 8)
check(f"Python >= 3.8  (当前: {sys.version.split()[0]})", py_ok)

# ── 2. PyTorch ──────────────────────────────────────────────────
section("2. PyTorch")
try:
    import torch
    check(f"PyTorch 已安装  (版本: {torch.__version__})", True)
    xpu_native = hasattr(torch, 'xpu') and torch.xpu.is_available()
    check("torch.xpu.is_available() [PyTorch >= 2.4 原生 XPU]", xpu_native,
          detail="" if xpu_native else "需要 PyTorch >= 2.4 且已安装 Intel GPU 驱动")
except ImportError:
    check("PyTorch 已安装", False, detail="pip install torch")

# ── 3. Intel Extension for PyTorch (IPEX) ───────────────────────
section("3. Intel Extension for PyTorch (IPEX)")
try:
    import intel_extension_for_pytorch as ipex
    check(f"IPEX 已安装  (版本: {ipex.__version__})", True)
    xpu_ipex = ipex.xpu.is_available()
    dev_count = ipex.xpu.device_count() if xpu_ipex else 0
    check(f"ipex.xpu.is_available()  ({dev_count} 个 XPU 设备)", xpu_ipex,
          detail="" if xpu_ipex else "检查 Intel GPU 驱动是否已安装 (/dev/dri 是否存在)")
    if xpu_ipex:
        for i in range(dev_count):
            props = ipex.xpu.get_device_properties(i)
            check(f"XPU[{i}]: {props.name}", True,
                  detail=f"显存: {props.total_memory // 1024**2} MB")
except ImportError:
    check("IPEX 已安装", False,
          detail="pip install intel-extension-for-pytorch")

# ── 4. /dev/dri 设备节点 ────────────────────────────────────────
section("4. Intel GPU 驱动 (/dev/dri)")
import os
from pathlib import Path
dri_exists = Path("/dev/dri").exists()
check("/dev/dri 目录存在", dri_exists,
      detail="" if dri_exists else "Intel GPU 驱动未安装或不在容器内")
if dri_exists:
    nodes = list(Path("/dev/dri").iterdir())
    for n in nodes:
        check(f"  {n}", True)

# ── 5. OpenVINO / NPU ───────────────────────────────────────────
section("5. OpenVINO & Intel NPU")
try:
    import onnxruntime as ort
    providers = ort.get_available_providers()
    check(f"onnxruntime 已安装  (版本: {ort.__version__})", True)
    ov_ok = "OpenVINOExecutionProvider" in providers
    check("OpenVINOExecutionProvider 可用 [Intel NPU/GPU]", ov_ok,
          detail="可用 Providers: " + ", ".join(providers))
    if ov_ok:
        try:
            import openvino as ov
            core = ov.Core()
            devices = core.available_devices
            check(f"OpenVINO 设备: {devices}", True)
            check("NPU 设备存在", "NPU" in devices,
                  detail="" if "NPU" in devices else "当前主机无 Intel NPU 或驱动未安装")
        except Exception as e:
            check("OpenVINO Core 初始化", False, detail=str(e))
except ImportError:
    check("onnxruntime 已安装", False,
          detail="pip install onnxruntime  或  pip install onnxruntime-openvino")

# ── 6. Docker / Podman ──────────────────────────────────────────
section("6. 容器运行时")
for runtime in ["docker", "podman"]:
    try:
        result = subprocess.run([runtime, "--version"],
                                capture_output=True, text=True, timeout=5)
        ok = result.returncode == 0
        ver = result.stdout.strip().splitlines()[0] if ok else result.stderr.strip()
        check(f"{runtime} 已安装", ok, detail=ver)
    except FileNotFoundError:
        check(f"{runtime} 已安装", False, detail="未找到命令")

# ── 7. 综合建议 ──────────────────────────────────────────────────
section("综合建议")
try:
    xpu_ready = (ipex.xpu.is_available()
                 if 'ipex' in dir() else
                 (hasattr(torch, 'xpu') and torch.xpu.is_available()
                  if 'torch' in dir() else False))
except Exception:
    xpu_ready = False

try:
    npu_ready = "OpenVINOExecutionProvider" in ort.get_available_providers()
except Exception:
    npu_ready = False

if xpu_ready:
    print("\n  ✅ 环境就绪，推荐使用 DEVICE=xpu 启动服务")
    print("     docker compose -f docker-compose.intel.yml up -d")
elif npu_ready:
    print("\n  ✅ NPU 就绪，推荐使用 DEVICE=npu 启动服务")
    print("     DEVICE=npu python3 api_server.py")
else:
    print("\n  ⚠️  未检测到 Intel GPU/NPU，将使用 CPU 模式")
    print("     DEVICE=cpu python3 api_server.py")

print()
