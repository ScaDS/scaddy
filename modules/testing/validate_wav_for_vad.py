import wave
import webrtcvad
from pydub import AudioSegment
import os

vad = webrtcvad.Vad(3)

def convert_to_pcm_format(audio_path, target_path):
    audio = AudioSegment.from_wav(audio_path)
    audio = audio.set_frame_rate(16000)  # Samplerate auf 16000 Hz setzen
    audio = audio.set_channels(1)  # Mono
    audio = audio.set_sample_width(2)  # 16-bit PCM
    audio.export(target_path, format="wav")
    
    # Verifiziere die Konvertierung
    with wave.open(target_path, 'rb') as wf:
        if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getframerate() != 16000:
            raise ValueError("Fehler bei der Konvertierung: Datei hat nicht das erwartete Format")

def validate_speech_content(audio_path):
    print("...checking for voice activity in temp-audio .wav again:")
    
    # Konvertiere die Audiodatei ins richtige Format
    temp_converted_path = audio_path.replace(".wav", "_converted.wav")
    convert_to_pcm_format(audio_path, temp_converted_path)
    try:
        with wave.open(temp_converted_path, 'rb') as wf:
            sample_rate = wf.getframerate()
            frame_duration = 30  # Dauer des Frames in Millisekunden
            frame_size = int(sample_rate * frame_duration / 1000)  # Anzahl der Samples pro Frame

            # Schleife durch die Audiodatei und prüfe jeden Frame einzeln
            while True:
                frames = wf.readframes(frame_size)
                if len(frames) == 0:
                    break  # Ende der Datei erreicht
                
                if vad.is_speech(frames, sample_rate):
                    print("temp-audio is voice, starting further processing...")
                    return True

        print("Keine Sprachaktivität erkannt. Datei wird verworfen.")
        return False
    except Exception as e:
        print(f"Fehler bei der VAD-Validierung: {e}")
        raise

# Dateipfad der zu überprüfenden Datei
audio_path = "./temp_audio/test.wav"

# Sprachaktivität prüfen
is_voice = validate_speech_content(audio_path)

if is_voice:
    print("Sprachaktivität erkannt.")
else:
    print("Keine Sprachaktivität erkannt.")
