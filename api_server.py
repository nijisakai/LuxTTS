#!/usr/bin/env python3
"""
LuxTTS API Server
启动后访问: http://localhost:9880/?text=你好&speaker=audio/ref.wav
"""

import io
import os
import logging
import hashlib
from pathlib import Path

import torch
import soundfile as sf
from flask import Flask, request, Response, jsonify

from zipvoice.luxvoice import LuxTTS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ── 全局模型实例 & prompt 缓存 ──────────────────────────────────────
tts_model: LuxTTS = None
prompt_cache: dict = {}          # {文件路径hash: encode_dict}

DEVICE = os.getenv("DEVICE", "cuda" if torch.cuda.is_available() else "cpu")
THREADS = int(os.getenv("THREADS", "4"))
NUM_STEPS = int(os.getenv("NUM_STEPS", "4"))
GUIDANCE_SCALE = float(os.getenv("GUIDANCE_SCALE", "3.0"))
T_SHIFT = float(os.getenv("T_SHIFT", "0.5"))
SPEED = float(os.getenv("SPEED", "1.0"))
RMS = float(os.getenv("RMS", "0.01"))
REF_DURATION = int(os.getenv("REF_DURATION", "5"))
PORT = int(os.getenv("PORT", "9880"))
SAMPLE_RATE = 48000


def load_model():
    """加载模型到全局变量"""
    global tts_model
    logger.info("正在加载 LuxTTS 模型 (device=%s) ...", DEVICE)
    tts_model = LuxTTS("YatharthS/LuxTTS", device=DEVICE, threads=THREADS)
    logger.info("模型加载完成")


def get_encoded_prompt(speaker_path: str) -> dict:
    """对参考音频做编码，带缓存"""
    path = Path(speaker_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"参考音频不存在: {path}")

    key = hashlib.sha256(str(path).encode()).hexdigest()
    if key not in prompt_cache:
        logger.info("编码参考音频: %s", path)
        prompt_cache[key] = tts_model.encode_prompt(str(path), duration=REF_DURATION, rms=RMS)
    return prompt_cache[key]


@app.route("/", methods=["GET", "POST"])
def synthesize():
    """
    TTS 合成接口
    GET/POST 参数:
      text     - 待合成文本 (必填)
      speaker  - 参考音频路径 (必填)
    返回 WAV 音频流
    """
    if request.method == "POST":
        if request.is_json:
            data = request.get_json(silent=True) or {}
            text = data.get("text")
            speaker = data.get("speaker")
        else:
            text = request.form.get("text")
            speaker = request.form.get("speaker")
    else:
        text = request.args.get("text")
        speaker = request.args.get("speaker")

    if not text:
        return jsonify({"error": "缺少 text 参数"}), 400
    if not speaker:
        return jsonify({"error": "缺少 speaker 参数"}), 400

    try:
        encoded_prompt = get_encoded_prompt(speaker)
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404

    logger.info("合成文本: %s | 参考音色: %s", text, speaker)

    try:
        wav = tts_model.generate_speech(
            text,
            encoded_prompt,
            num_steps=NUM_STEPS,
            guidance_scale=GUIDANCE_SCALE,
            t_shift=T_SHIFT,
            speed=SPEED,
        )
        wav_np = wav.numpy().squeeze()

        buf = io.BytesIO()
        sf.write(buf, wav_np, SAMPLE_RATE, format="WAV")
        buf.seek(0)

        return Response(buf.read(), mimetype="audio/wav",
                        headers={"Content-Disposition": "inline; filename=output.wav"})
    except Exception as e:
        logger.exception("合成失败")
        return jsonify({"error": f"合成失败: {e}"}), 500


@app.route("/health", methods=["GET"])
def health():
    """健康检查"""
    return jsonify({"status": "ok", "device": DEVICE})


if __name__ == "__main__":
    load_model()
    app.run(host="0.0.0.0", port=PORT, threaded=False)
