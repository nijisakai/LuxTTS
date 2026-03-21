@echo off
chcp 65001 >nul
title LuxTTS NPU 安装器

echo ============================================
echo   LuxTTS NPU 版 - Windows 安装脚本
echo   适用于 Intel Core Ultra (带 NPU) 处理器
echo ============================================
echo.

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/5] 创建虚拟环境...
if not exist ".venv" (
    python -m venv .venv
)
call .venv\Scripts\activate.bat

echo [2/5] 升级 pip 并安装基础工具...
python -m pip install --upgrade pip
pip install uv

echo [3/5] 安装 CPU 版 PyTorch（NPU 推理由 OpenVINO 处理）...
uv pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu

echo [4/5] 安装项目依赖...
uv pip install -r requirements.txt
uv pip install flask soundfile

echo [5/6] 安装 OpenVINO Runtime（需与 onnxruntime-openvino 版本匹配）...
uv pip install "openvino>=2025.1,<2026"

echo [6/6] 安装 onnxruntime-openvino（Intel NPU 加速）...
uv pip install --force-reinstall onnxruntime-openvino

echo.
echo ============================================
echo   安装完成！
echo   运行 start-npu.bat 启动服务
echo ============================================
pause
