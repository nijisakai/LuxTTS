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
prompt_cache: dict = {}          # {cache_key: encode_dict}

def _detect_device() -> str:
    """自动检测可用设备：cuda > xpu（Intel Arc）> cpu"""
    if torch.cuda.is_available():
        return "cuda"
    try:
        import intel_extension_for_pytorch as ipex  # noqa: F401
        if torch.xpu.is_available():
            return "xpu"
    except ImportError:
        pass
    return "cpu"

DEVICE = os.getenv("DEVICE", _detect_device())
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


def get_encoded_prompt(speaker_path: str, duration: int, rms: float) -> dict:
    """对参考音频做编码，带缓存（缓存 key 包含 duration 和 rms）"""
    path = Path(speaker_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"参考音频不存在: {path}")

    key = hashlib.sha256(f"{path}|{duration}|{rms}".encode()).hexdigest()
    if key not in prompt_cache:
        logger.info("编码参考音频: %s (duration=%d, rms=%s)", path, duration, rms)
        prompt_cache[key] = tts_model.encode_prompt(str(path), duration=duration, rms=rms)
    return prompt_cache[key]


def _get_param(data: dict, name: str, default, cast):
    """从请求参数中获取值，不存在则用默认值，转换失败则用默认值"""
    val = data.get(name)
    if val is None:
        return default
    try:
        return cast(val)
    except (ValueError, TypeError):
        return default


def _str_to_bool(val) -> bool:
    """字符串转布尔值"""
    if isinstance(val, bool):
        return val
    return str(val).lower() in ("true", "1", "yes")


@app.route("/", methods=["GET", "POST"])
def synthesize():
    """
    TTS 合成接口
    GET/POST 参数:
      text           - 待合成文本 (必填)
      speaker        - 参考音频路径 (必填)
      num_steps      - 采样步数，默认 4
      guidance_scale - 引导尺度，默认 3.0
      t_shift        - 采样温度，默认 0.5
      speed          - 语速，默认 1.0
      rms            - 音量控制，默认 0.01
      ref_duration   - 参考音频最大时长(秒)，默认 5
      return_smooth  - 平滑模式(true/false)，默认 false
    返回 WAV 音频流
    """
    if request.method == "POST":
        if request.is_json:
            data = request.get_json(silent=True) or {}
        else:
            data = request.form.to_dict()
    else:
        data = request.args.to_dict()

    text = data.get("text")
    speaker = data.get("speaker")

    if not text:
        return jsonify({"error": "缺少 text 参数"}), 400
    if not speaker:
        return jsonify({"error": "缺少 speaker 参数"}), 400

    # 解析可选参数，未指定则使用环境变量默认值
    num_steps = _get_param(data, "num_steps", NUM_STEPS, int)
    guidance_scale = _get_param(data, "guidance_scale", GUIDANCE_SCALE, float)
    t_shift = _get_param(data, "t_shift", T_SHIFT, float)
    speed = _get_param(data, "speed", SPEED, float)
    rms = _get_param(data, "rms", RMS, float)
    ref_duration = _get_param(data, "ref_duration", REF_DURATION, int)
    return_smooth = _str_to_bool(data.get("return_smooth", False))

    try:
        encoded_prompt = get_encoded_prompt(speaker, ref_duration, rms)
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404

    logger.info(
        "合成文本: %s | 参考音色: %s | steps=%d scale=%.1f t_shift=%.2f speed=%.1f smooth=%s",
        text, speaker, num_steps, guidance_scale, t_shift, speed, return_smooth,
    )

    try:
        wav = tts_model.generate_speech(
            text,
            encoded_prompt,
            num_steps=num_steps,
            guidance_scale=guidance_scale,
            t_shift=t_shift,
            speed=speed,
            return_smooth=return_smooth,
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
