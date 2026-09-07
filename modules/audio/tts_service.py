import os
import tempfile
import asyncio
import json
import base64
import re
from openai import OpenAI

from modules.backend_config import (
    TTS_BASE_URL,
    TTS_API_KEY,
    TTS_MODEL,
    TTS_VOICE,
)


# Hilfsfunktion: Config laden (gleiches Schema wie modules/llm/agents_service.py)
def load_config():
    try:
        with open("config/config.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"tts_voice": TTS_VOICE}


global stream
stream = None


class TTSService:
    """
    Text-to-Speech Service.

    Nutzt einen OpenAI-kompatiblen /audio/speech Endpoint. Der Endpoint, das
    Modell und die Voice werden über .env konfiguriert (siehe modules/backend_config.py).

    Beispiele:
        - llm.scads.ai (ScaDS Living Lab, OmniVoice)
        - api.openai.com (OpenAI, tts-1 / tts-1-hd)
        - Kokoro-FastAPI (lokal, kokoro)
        - openedai-speech (lokal)
    """

    def __init__(self):
        self.openai_client = OpenAI(
            base_url=TTS_BASE_URL,
            api_key=TTS_API_KEY,
        )

    def _get_tts_model(self) -> str:
        """Liest das TTS-Modell (kann später aus config.json überschrieben werden)."""
        return load_config().get("tts_model", TTS_MODEL)

    def _get_tts_voice(self) -> str:
        """Liest die TTS-Voice aus config.json (hot-reload)."""
        return load_config().get("tts_voice", TTS_VOICE)

    async def get_audio_single_sentence_openai(self, text: str) -> dict:
        """
        Generiert Audio für einen einzelnen Satz via OpenAI-kompatibler API.

        Returns:
            dict: {"type": "tts_sentence", "text": str, "audio": base64_str}
        """
        processed_text = self.preprocess_text_for_tts(text)
        voice = self._get_tts_voice()
        model = self._get_tts_model()

        response = self.openai_client.audio.speech.create(
            model=model,
            voice=voice,
            input=processed_text,
            response_format="mp3",
        )
        audio_data = response.content

        # Base64-kodiert als JSON zurückschicken
        message = {
            "type": "tts_sentence",
            "text": text,
            "audio": base64.b64encode(audio_data).decode("utf-8"),
        }
        return message

    def preprocess_text_for_tts(self, text: str) -> str:
        """
        Bereinigt Text für TTS:
        - Ersetzt Sonderzeichen/Markdown die als 'Asterisk' gesprochen werden
        - Entfernt Emojis die sonst buchstabiert werden
        - Korrigiert bekannte Aussprache-Probleme

        Args:
            text (str): Rohtext

        Returns:
            str: Bereinigter Text für TTS
        """
        # Aussprache-Korrekturen
        text = re.sub(r"\b(ScaDS\.AI)\b", "Scads AI", text, flags=re.IGNORECASE)
        text = re.sub(r"\b(ScaDS)\b", "Scads", text, flags=re.IGNORECASE)

        # Markdown-Zeichen entfernen, die TTS sonst vorliest
        # (*, _, ` werden zu 'Asterisk', 'Underscore', 'Backtick')
        text = re.sub(r"[*_`~]+", "", text)

        # Doppelte Leerzeichen reduzieren
        text = re.sub(r"  +", " ", text).strip()

        return text

    def stop_audio(self):
        """Stop audio playback (no-op for API-based TTS)."""
        pass

    def shutdown(self):
        """Cleanup (no-op for API-based TTS)."""
        pass
