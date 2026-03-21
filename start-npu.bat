@echo off
chcp 65001 >nul
title LuxTTS NPU API Server

echo ============================================
echo   LuxTTS NPU API Server
echo   http://localhost:9880
echo ============================================
echo.

:: 激活虚拟环境
call .venv\Scripts\activate.bat

:: 将 OpenVINO DLL 加入 PATH（onnxruntime-openvino 依赖）
for /f "delims=" %%i in ('python -c "import openvino; import os; print(os.path.join(os.path.dirname(openvino.__file__), 'libs'))"') do set "OV_LIBS=%%i"
if defined OV_LIBS (
    set "PATH=%OV_LIBS%;%PATH%"
    echo OpenVINO libs: %OV_LIBS%
)

:: 先杀掉之前占用端口的进程
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":9880.*LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

:: 环境变量配置
set DEVICE=npu
set OPENVINO_DEVICE=NPU
set PORT=9880
set NUM_STEPS=4
set GUIDANCE_SCALE=3.0
set T_SHIFT=0.5
set SPEED=1.0
set RMS=0.01
set REF_DURATION=5
set THREADS=4
:: Windows 原生环境可直连 huggingface.co，不设 HF_ENDPOINT
:: 如需镜像可取消下行注释:
:: set HF_ENDPOINT=https://hf-mirror.com

echo 设备: Intel NPU (OpenVINO)
echo 端口: %PORT%
echo.
echo 首次运行会自动下载模型（约1.4GB），请耐心等待...
echo 启动后访问: http://localhost:%PORT%/?text=你好
echo.

python api_server.py

pause
