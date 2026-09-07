from enum import Enum
import re
from openai import OpenAI
from typing import Optional
from faster_whisper import WhisperModel
import json

from modules.backend_config import (
    STT_API_BASE_URL,
    STT_API_KEY,
    STT_API_MODEL,
    WHISPER_MODEL_SIZE,
    WHISPER_DEVICE,
    WHISPER_COMPUTE_TYPE,
)

# Hilfsfunktion: Config laden
def load_config():
    try:
        with open("config/config.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"local": True}

class STTMode(Enum):
    LOCAL = "local"
    API = "api"

class STTService:
    config = load_config() # load config (/config/config.json)
    use_local = config.get("stt_local", True) # check if local model (faster_whisper) should be used or remote model (openai-whisper-api)
    if use_local:
        STTMode_Var = STTMode.LOCAL
    else:
        STTMode_Var = STTMode.API

    def __init__(self, mode: STTMode = STTMode_Var, device: str = "cuda"):
        """
        Initialize the STT service with specified mode.
        
        Args:
            mode (STTMode): Choose between LOCAL or API implementation
            device (str): Device to use for local implementation ("cuda" or "cpu")
        """
        self.mode = mode
        self.client = OpenAI(
            base_url=STT_API_BASE_URL,
            api_key=STT_API_KEY,
        ) if mode == STTMode.API else None
        
        if mode == STTMode.LOCAL:
            try:
                from faster_whisper import WhisperModel
                self.model = WhisperModel(
                    WHISPER_MODEL_SIZE,
                    device=WHISPER_DEVICE,
                    compute_type=WHISPER_COMPUTE_TYPE,
                )
            except ImportError:
                raise ImportError("faster-whisper is required for local mode. Install it with 'pip install faster-whisper'")
        else:
            self.model = None

    def transcribe_audio(self, audio_path: str, lang: str) -> str:
        """
        Transcribes the recorded audio using either local model or OpenAI API.
        
        Args:
            audio_path (str): Path to the audio file
            
        Returns:
            str: Transcribed text
        """
        if self.mode == STTMode.API:
            try:
                with open(audio_path, "rb") as audio_file:
                    transcription = self.client.audio.transcriptions.create(
                        model=STT_API_MODEL,
                        file=audio_file,
                        language=lang
                    )
                return self.post_process_transcription(transcription.text)
            except Exception as e:
                print(f"Error during API transcription: {str(e)}")
                return ""
        else:
            try:
                segments, _ = self.model.transcribe(audio_path, language=lang, word_timestamps=True, task="transcribe")
                transcription = " ".join([segment.text for segment in segments])
                return self.post_process_transcription(transcription)
            except Exception as e:
                print(f"Error during local transcription: {str(e)}")
                return ""

    def post_process_transcription(self, text: str) -> str:
        """
        Post-processes the transcribed text to correct known mishearings.
        Customize the patterns below for your domain/brand name.
        
        Args:
            text (str): Raw transcribed text
            
        Returns:
            str: Processed text with corrected names
        """
        # Correct common mishearings of "ScaDS" / "ScaDS.AI"
        scads_pattern = r'\b(skatz|SCATS|skatz\.ai|SCATS AI|Guts|Skat|Schatz|SCUTS|GATS|Gats|SCUDS|Scots|Skats AI|Skats|skatzt|Skatzt)\b'
        def replace_match(match):
            wrong_name = match.group(0).lower()
            if '.ai' in wrong_name or 'ai' in wrong_name:
                return "ScaDS.AI"
            return "ScaDS"
        text = re.sub(scads_pattern, replace_match, text, flags=re.IGNORECASE)

        # Correct common mishearings of the assistant's name "Scaddy"
        scaddy_pattern = r'\b(scotty|skedi|geri|gerri|garry|skelly|skally|Gerdi|sketchy|Eddy|Scatty|Scaredy|caddy|Skadi|Getty|Skeddie|Scady|Scary|Sketti|Eddie|Geddy|Muskeli|skatty|Skitty|Steady)\b'
        text = re.sub(scaddy_pattern, 'Scaddy', text, flags=re.IGNORECASE)

        return text
