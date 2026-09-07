"""
Zentrale Backend-Konfiguration für Scaddy.

Alle Dienste (LLM/Chat, VLM, TTS, STT-API) sind OpenAI-kompatibel und werden
über Umgebungsvariablen (siehe .env) konfiguriert. Defaults zeigen auf den
ScaDS-HPC-Endpoint (llm.scads.ai), können aber auf beliebige OpenAI-kompatible
Server zeigen (OpenAI, llama.cpp llama-server, vLLM, LM Studio, etc.).

Fallback-Logik für API-Keys:
    LLM_API_KEY → SCADS_AI_HPC_API_KEY → ""
    TTS_API_KEY → LLM_API_KEY          (gleicher Server)
    VLM_API_KEY → LLM_API_KEY          (gleicher Server)

Verwendung in Services:
    from modules.backend_config import LLM_BASE_URL, LLM_MODEL, LLM_API_KEY
    requests.post(f"{LLM_BASE_URL}/chat/completions", ...)
"""

import os


# ============================================================
# LLM (Chat) — für die Hauptkonversation
# ============================================================
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://llm.scads.ai/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", os.getenv("SCADS_AI_HPC_API_KEY", ""))
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")


# ============================================================
# VLM (Vision Language Model) — für Bildbeschreibung / OCR
# ============================================================
# Default: gleiche Instanz wie LLM (ScaDS kombiniert beide Dienste auf einem Server)
VLM_BASE_URL = os.getenv("VLM_BASE_URL", LLM_BASE_URL)
VLM_API_KEY = os.getenv("VLM_API_KEY", LLM_API_KEY)
VLM_MODEL = os.getenv("VLM_MODEL", "alias-vision")


# ============================================================
# TTS (Text-to-Speech) — OpenAI-kompatibler /audio/speech Endpoint
# ============================================================
TTS_BASE_URL = os.getenv("TTS_BASE_URL", "https://llm.scads.ai/v1")
TTS_API_KEY = os.getenv("TTS_API_KEY", LLM_API_KEY)
TTS_MODEL = os.getenv("TTS_MODEL", "OmniVoice")
TTS_VOICE = os.getenv("TTS_VOICE", "alloy")


# ============================================================
# STT-API (Speech-to-Text via REST, nur wenn STT_LOCAL=false)
# ============================================================
STT_API_BASE_URL = os.getenv("STT_API_BASE_URL", "https://api.openai.com/v1")
STT_API_KEY = os.getenv("STT_API_KEY", os.getenv("OPENAI_API_KEY", ""))
STT_API_MODEL = os.getenv("STT_API_MODEL", "whisper-1")


# ============================================================
# Lokale Modellkonfiguration
# ============================================================
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "medium")  # tiny|base|small|medium|large-v3
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cuda")  # cuda | cpu
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "float16")  # float16|float32|int8

CLIP_MODEL = os.getenv("CLIP_MODEL", "openai/clip-vit-base-patch32")
CLIP_DEVICE = os.getenv("CLIP_DEVICE", "cuda")  # cuda | cpu


def get_tts_config() -> dict:
    """Liefert die TTS-Konfiguration als Dict (für tts_service.py)."""
    return {
        "base_url": TTS_BASE_URL,
        "api_key": TTS_API_KEY,
        "model": TTS_MODEL,
        "voice": TTS_VOICE,
    }


def get_vlm_config() -> dict:
    """Liefert die VLM-Konfiguration als Dict (für vlm_service.py)."""
    return {
        "base_url": VLM_BASE_URL,
        "api_key": VLM_API_KEY,
        "model": VLM_MODEL,
    }


def get_stt_api_config() -> dict:
    """Liefert die STT-API-Konfiguration als Dict (für stt_service.py, nur wenn remote)."""
    return {
        "base_url": STT_API_BASE_URL,
        "api_key": STT_API_KEY,
        "model": STT_API_MODEL,
    }


def get_llm_config() -> dict:
    """Liefert die LLM-Konfiguration als Dict (für agents_service.py)."""
    return {
        "base_url": LLM_BASE_URL,
        "api_key": LLM_API_KEY,
        "model": LLM_MODEL,
    }


def get_whisper_config() -> dict:
    """Liefert die Whisper-Konfiguration als Dict (für stt_service.py, nur wenn lokal)."""
    return {
        "model_size": WHISPER_MODEL_SIZE,
        "device": WHISPER_DEVICE,
        "compute_type": WHISPER_COMPUTE_TYPE,
    }


def get_clip_config() -> dict:
    """Liefert die CLIP-Konfiguration als Dict (für clip_service.py)."""
    return {
        "model": CLIP_MODEL,
        "device": CLIP_DEVICE,
    }
