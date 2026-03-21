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
set HF_ENDPOINT=https://hf-mirror.com

echo 设备: Intel NPU (OpenVINO)
echo 端口: %PORT%
echo.
echo 首次运行会自动下载模型（约1.4GB），请耐心等待...
echo 启动后访问: http://localhost:%PORT%/?text=你好^&speaker=audio/花魁.wav
echo.

python api_server.py

pause
