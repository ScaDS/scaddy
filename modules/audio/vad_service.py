import os
import torch
from silero_vad import get_speech_timestamps, read_audio


class VADService:
    def __init__(self):
        # Set User Cache:
        # Check path of repo-root
        repo_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )  # eine Ebene höher
        print(repo_root)
        # Set TORCH_HOME to <repo_root>/models if not already set (e.g. by Docker)
        os.environ.setdefault("TORCH_HOME", os.path.join(repo_root, "models"))
        # print("TORCH_HOME set to:", os.environ["TORCH_HOME"])
        # Silero-VAD Modell laden
        self.model, utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad", model="silero_vad", force_reload=False
        )
        (self.get_speech_timestamps, _, self.read_audio, _, _) = utils

    def validate_speech_content(self, audio_path):
        """
        Überprüft, ob das Audio Sprachaktivität enthält.
        """
        try:
            # Silero-VAD Validierung
            wav = self.read_audio(audio_path, sampling_rate=16000)
            speech_timestamps = self.get_speech_timestamps(
                wav, self.model, sampling_rate=16000
            )

            if speech_timestamps:
                print("Silero-VAD hat Sprachaktivität erkannt.")
                return True
            else:
                print(
                    "Silero-VAD hat keine Sprachaktivität erkannt. Datei wird verworfen."
                )
                return False
        except Exception as e:
            print(f"Fehler bei der VAD-Validierung: {e}")
            raise
