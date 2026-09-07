import torch
import torchaudio
from silero_vad import get_speech_timestamps, read_audio

# Silero-VAD Modell laden
model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad', model='silero_vad', force_reload=True)
(get_speech_timestamps, _, read_audio, _, _) = utils

def validate_with_silero(audio_path):
    # Lade die Audiodatei
    wav = read_audio(audio_path, sampling_rate=16000)
    
    # Sprachsegmente erkennen
    speech_timestamps = get_speech_timestamps(wav, model, sampling_rate=16000)

    if speech_timestamps:
        print("Silero-VAD hat Sprachaktivität erkannt.")
        return True
    else:
        print("Silero-VAD hat keine Sprachaktivität erkannt.")
        return False

# Beispielverwendung
audio_path = "../temp_audio/tmp21_2b25k.wav"
is_speech = validate_with_silero(audio_path)
