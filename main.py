"""
Scaddy — Multi-Agent Conversational AI for Living Lab Tours.

Single-process FastAPI app serving a static SPA frontend plus
speech/vision/LLM services. German is the working language for comments,
UI text, and prompts.

Endpoints:
    /                           — Vue.js SPA (frontend/static/index.html)
    /ws                         — WebSocket (STT results, LLM answers)
    /audio_enabled_conversation — Main conversation route (audio + optional image)
    /tts_single_sentence        — TTS for a single sentence
    /reset                      — Reset conversation protocol
    /set_language               — Set frontend language (de/en)
    /add_to_conversation_protocol — Add entry to conversation protocol
    /stt_knowledge_annotation   — STT for image annotation (knowledge mode)
    /add_clip_embedding         — Add CLIP embedding for visRAG
    /admin/config               — Admin panel (config.html)
    /admin/update_config        — Save config (POST)
    /admin/delete_embedding     — Delete visual embedding (POST)
    /admin/edit_cag             — Edit knowledge base (edit_cag.html)
    /admin/save_cag             — Save knowledge base (POST)
    /stop_tts                   — Stop TTS playback
"""

###############
#
# Imports
#
###############
import os

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# Check path of repo-root
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
print("Repo-Root: ", repo_root)
# Set TORCH_HOME/HF_HOME to <repo_root>/models if not already set (e.g. by Docker)
os.environ.setdefault("TORCH_HOME", os.path.join(repo_root, "models"))
os.environ.setdefault("HF_HOME", os.path.join(repo_root, "models"))
print("TORCH_HOME:", os.environ["TORCH_HOME"])
print("HF_HOME:", os.environ["HF_HOME"])

# .env
from dotenv import load_dotenv

load_dotenv()

# imports for FastAPI
from fastapi import FastAPI, UploadFile, File, Form, Request, WebSocket
from fastapi import WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import (
    HTMLResponse,
    RedirectResponse,
    FileResponse,
    JSONResponse,
)

# project module imports
from modules.audio.vad_service import VADService
from modules.audio.stt_service import STTService
from modules.audio.tts_service import TTSService
from modules.llm.agents_service import OpenAIAgentsService
from modules.protocol.conversation_protocol import ConversationProtocol
from modules.vision.clip_service import CLIPService
from modules.vision.vlm_service import VLMService

# misc libraries
import json
import threading
import uvicorn
import base64
import subprocess
from pydub import AudioSegment
import logging
import io
from io import BytesIO
from PIL import Image
import asyncio
#
# --- end of imports ---

###############
#
# initialization
#
###############
# logging init
logging.basicConfig(level=logging.INFO)

# init FastAPI instance
app = FastAPI()

# CORS for multi-origin file permissions
# (e.g. for audio-file handling and multi-os/browser support of audio playback)
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Für Testzwecke, in der Produktion besser spezifische URLs angeben
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
admin_templates = Jinja2Templates(directory="admin/templates")

# WebSocket-Referenz (wird bei Verbindung gesetzt)
websocket: WebSocket = None

# --- Services initialisieren (module-level singletons) ---
vad_service = VADService()
stt_service = STTService()
agents_service = OpenAIAgentsService()
protocol_service = ConversationProtocol()
tts_service = TTSService()
clip_service = CLIPService()
vlm_service = VLMService()

AGENT_SERVICE = agents_service

frontend_language = "de"


class ConnectionManager:
    """
    Verwaltet alle aktiven WebSocket-Verbindungen.

    Mehrere Clients (z.B. Tablet + Admin-Browser) können gleichzeitig
    verbunden sein. broadcast() sendet an alle aktiven Verbindungen und
    räumt tote Verbindungen automatisch auf.
    """

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        if websocket not in self.active_connections:
            self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict) -> bool:
        """
        Sendet eine Nachricht an ALLE verbundenen Clients.

        Returns:
            bool: True wenn mindestens ein Client die Nachricht erhalten hat.
        """
        if not self.active_connections:
            print("[WS] ⚠ Keine aktiven Verbindungen — Nachricht verworfen")
            return False

        dead_connections = []
        sent_count = 0

        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
                sent_count += 1
            except Exception:
                dead_connections.append(connection)

        # Tote Verbindungen entfernen
        for dead in dead_connections:
            self.disconnect(dead)
            print(f"[WS] ✗ Tote Verbindung entfernt ({len(self.active_connections)} verbleibend)")

        if sent_count > 0:
            print(f"[WS] ✓ Nachricht an {sent_count} Client(s) gesendet")
        else:
            print("[WS] ⚠ Nachricht an keinen Client gesendet")

        return sent_count > 0

    @property
    def connection_count(self) -> int:
        return len(self.active_connections)


manager = ConnectionManager()

#
# --- end of initialization ---

###############
#
# helper functions
#
###############


def detect_audio_format(file_path: str) -> str:
    """
    Erkennt das Audio-Format anhand der Magic Bytes (Datei-Header).

    Unterstützte Formate:
        - wav   (RIFF....WAVE)
        - ogg   (OggS — z.B. Firefox MediaRecorder)
        - webm  (EBML — z.B. Chrome MediaRecorder)
        - mp3   (ID3 oder MPEG-Frame-Sync)
        - flac  (fLaC)
        - m4a   (ftyp bei Offset 4 — AAC/M4A)

    Returns:
        str: Format-String für pydub/ffmpeg ("wav", "ogg", "webm", ...)
    """
    with open(file_path, "rb") as f:
        header = f.read(16)

    # WAV: "RIFF" + "WAVE"
    if header[:4] == b"RIFF" and header[8:12] == b"WAVE":
        return "wav"

    # OGG: "OggS" (Firefox MediaRecorder: Opus in Ogg)
    if header[:4] == b"OggS":
        return "ogg"

    # WebM/Matroska: EBML Magic (Chrome MediaRecorder: Opus in WebM)
    if header[:4] == bytes([0x1A, 0x45, 0xDF, 0xA3]):
        return "webm"

    # MP3: "ID3" Tag oder MPEG Frame-Sync (0xFF 0xFB/0xF3/0xF2)
    if header[:3] == b"ID3" or (header[0] == 0xFF and (header[1] & 0xE0) == 0xE0):
        return "mp3"

    # FLAC: "fLaC"
    if header[:4] == b"fLaC":
        return "flac"

    # M4A/AAC: "ftyp" bei Offset 4
    if header[4:8] == b"ftyp":
        return "m4a"

    # Unbekannt: Standard WAV annehmen
    return "wav"


#
# --- end of helper functions ---

###############
#
# routes
#
###############


@app.websocket("/ws")
async def connect_websocket(newWebsocket: WebSocket):
    """WebSocket for receiving/sending text."""
    global websocket
    client_info = f"{newWebsocket.client.host}:{newWebsocket.client.port}"
    print(f"[WS] ✓ Verbindung angenommen von {client_info}")

    await manager.connect(newWebsocket)
    websocket = newWebsocket
    print(f"[WS] ✓ {manager.connection_count} aktive Verbindung(en)")

    try:
        while True:
            data = await newWebsocket.receive_text()
            print(f"[WS] ◀ Daten empfangen von {client_info}: {data[:100]}")
    except WebSocketDisconnect:
        print(f"[WS] ✗ Verbindung getrennt: {client_info}")
        manager.disconnect(newWebsocket)
        if websocket is newWebsocket:
            websocket = None
    except Exception as e:
        print(f"[WS] ✗ Verbindung getrennt: {client_info}, Fehler: {type(e).__name__}: {e}")
        manager.disconnect(newWebsocket)
        if websocket is newWebsocket:
            websocket = None


# index route that returns the Vue single page application as a static .html file
@app.get("/", response_class=FileResponse)
async def get_index():
    return FileResponse("frontend/static/index.html")


@app.post("/set_language")
async def set_language(request: Request, lang: str):
    if not (lang == "de" or lang == "en"):
        return {"error": "Language code must be 'de' or 'en'"}
    global frontend_language
    frontend_language = lang
    return {"message": "Setting language successfull."}


@app.post("/audio_enabled_conversation")
async def audio_enabled_conversation(
    recording: UploadFile = File(...), image: UploadFile = File(None)
):
    """
    Haupt-Konversationsroute.

    Empfängt eine Audioaufnahme (und optional ein Bild), führt
    VAD → STT → (CLIP + VLM falls Bild) → Multi-Agent-LLM aus
    und pusht das Ergebnis über den WebSocket.
    """
    # Ensure temp directories exist
    os.makedirs("runtime/temp_audio", exist_ok=True)
    os.makedirs("runtime/temp_images", exist_ok=True)

    # Save audio file
    audio_directory = "runtime/temp_audio"
    original_audio_path = os.path.join(audio_directory, "recording.raw")
    converted_audio_path = os.path.join(audio_directory, "question.wav")

    with open(original_audio_path, "wb") as f:
        f.write(await recording.read())

    # Audio immer in 16kHz Mono WAV konvertieren (VAD/STT-Anforderung).
    # Der Browser sendet via MediaRecorder OGG/Opus (Firefox) oder
    # WebM/Opus (Chrome) — NICHT WAV, egal wie der Dateiname lautet.
    # Konvertierung via ffmpeg direkt (pydub hat Probleme mit Opus-OGG).
    audio_format = detect_audio_format(original_audio_path)
    print(f"[Audio] Datei gespeichert: {original_audio_path}")
    print(f"[Audio] Erkanntes Format: {audio_format}")
    print(f"[Audio] Dateigröße: {os.path.getsize(original_audio_path)} Bytes")

    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-f", audio_format,       # Eingabe-Format explizit (Magic-Byte-Detection)
        "-i", original_audio_path,
        "-ar", "16000",           # 16kHz (Whisper/VAD requirement)
        "-ac", "1",               # Mono
        "-sample_fmt", "s16",     # 16-bit PCM
        converted_audio_path,
    ]
    print(f"[Audio] ffmpeg-Befehl: {' '.join(ffmpeg_cmd)}")

    try:
        result = subprocess.run(
            ffmpeg_cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {result.stderr[-300:]}")

        if not os.path.exists(converted_audio_path):
            raise RuntimeError("ffmpeg produced no output file")

        print(f"[Audio] Konvertierung OK: {converted_audio_path} "
              f"({os.path.getsize(converted_audio_path)} Bytes)")

    except Exception as e:
        print(f"[Audio-Konvertierung fehlgeschlagen: {e}]")
        return {"error": f"Audio conversion failed: {type(e).__name__}"}
    finally:
        # Rohdaten aufräumen
        if os.path.exists(original_audio_path):
            os.remove(original_audio_path)

    # 🎤 Audio validieren (VAD)
    print(f"[Pipeline] Starte VAD-Validierung für {converted_audio_path}")
    tts_service.stop_audio()
    transcription = ""
    if not vad_service.validate_speech_content(converted_audio_path):
        print("[Pipeline] VAD: KEINE Sprache erkannt")
        transcription = ""
        await manager.broadcast(
            {"type": "stt_result", "text": "vad_service_error_no_voice"}
        )
    else:
        print("[Pipeline] VAD: Sprache erkannt → starte STT")
        transcription = stt_service.transcribe_audio(
            converted_audio_path, frontend_language
        )
        print(f"[Pipeline] STT-Ergebnis: '{transcription}'")
        await manager.broadcast(
            {"type": "stt_result", "text": transcription}
        )
    # 📜 Protokoll
    protocol_service.write_to_protocol("User", transcription)
    protocol_service.write_actual_question("User", transcription)

    # 🖼 Bild speichern / verarbeiten (visRAG: CLIP + VLM)
    image_description = ""
    if image:
        image_directory = "runtime/temp_images"
        image_path = os.path.join(image_directory, image.filename)
        with open(image_path, "wb") as image_file:
            image_file.write(await image.read())

        # Parallele Inferenz: CLIP synchron, VLM async
        image_data, similarity = clip_service.find_similar_image(image_path)
        vlm_task = asyncio.create_task(vlm_service.infer(image_path))
        vlm_caption = await vlm_task

        # image_data ist None, wenn:
        # - keine Embeddings gespeichert sind
        # - das Bild nicht lesbar war
        # In dem Fall: nur VLM-Beschreibung verwenden (Fallback)
        if image_data is None:
            image_description = f"{vlm_caption}"
            protocol_service.write_to_protocol(
                "VLM", f"Zusätzliche Analyse von VLM: {vlm_caption}"
            )

        elif similarity < 0.60:
            # Unbekanntes Bild → nur VLM-Beschreibung
            image_description = f"{vlm_caption}"
            protocol_service.write_to_protocol(
                "VLM", f"Zusätzliche Analyse von VLM: {vlm_caption}"
            )

        elif 0.60 <= similarity < 0.799:
            # Unsicher → CLIP-Titel + VLM-Beschreibung
            image_description = (
                f"Teile dem Nutzer mit, dass du dir nicht sicher bist, aber es vermutlich folgendes sein könnte: "
                f"Titel: {image_data['title']} Description: {image_data['description']} "
                f"Zusätzliche Analyse von VLM: {vlm_caption} "
                f"Teile NIEMALS die Similarity oder den Ähnlichkeitswert mit!"
            )
            protocol_service.write_to_protocol(
                "VLM",
                f"CLIP-Titel: {image_data['title']} | VLM: {vlm_caption}",
            )

        else:
            # Bekanntes Bild → CLIP-Titel + VLM-Beschreibung
            image_description = (
                f"Titel: {image_data['title']} "
                f"Description: {image_data['description']} "
                f"Similarity: {similarity:.2f} "
                f"Zusätzliche Analyse von VLM: {vlm_caption} "
                f"Teile NIEMALS die Similarity oder den Ähnlichkeitswert mit!"
            )
            protocol_service.write_to_protocol(
                "VLM",
                f"CLIP-Titel: {image_data['title']} | Similarity: {similarity:.2f} | VLM: {vlm_caption}",
            )

    # 🤖 LLM Antwort generieren (Multi-Agent-Pipeline)
    print(f"[Pipeline] Starte LLM-Antwortgenerierung...")
    print(f"[Pipeline] Aktive WS-Verbindungen: {manager.connection_count}")
    context = protocol_service.get_latest_context_window()
    response = await AGENT_SERVICE.generate_response(
        frontend_language, context, image_description
    )
    protocol_service.write_to_protocol("LLM", response)

    print(f"[Pipeline] LLM-Antwort generiert: '{(response or '')[:100]}...'")

    ws_sent = await manager.broadcast(
        {"type": "scaddy_answer", "text": response}
    )

    # 🔊 TTS: Wird satzweise vom Client über /tts_single_sentence angefragt
    # Die Antwort wird zusätzlich im HTTP-Body zurückgegeben (Fallback,
    # falls der Client keinen WebSocket empfangen hat).
    return {
        "message": "Text answer generated and sent to client",
        "transcription": transcription,
        "answer": response,
        "ws_sent": ws_sent,
    }


@app.post("/reset")
async def reset():
    """Setzt das Konversationsprotokoll zurück."""
    try:
        protocol_service.clear_protocol()
        tts_service.stop_audio()
        return {"message": "Protokoll zurückgesetzt"}
    except Exception as e:
        return {"error": f"Protokoll konnte nicht zurückgesetzt werden: {str(e)}"}


@app.post("/tts_single_sentence")
async def tts_single_sentence(request: Request):
    """Generiert Audio für einen einzelnen Satz via OpenAI-kompatiblem TTS-Endpoint."""
    tts_service.stop_audio()
    data = await request.json()
    text = data.get("text")
    if not text:
        return JSONResponse(content={"error": "no text specified"}, status_code=400)
    try:
        message = await tts_service.get_audio_single_sentence_openai(text)
        return message
    except Exception as e:
        # Wichtig fürs Debugging: kompletten Fehler ins Backend-Log schreiben,
        # damit ungültige voice-Namen o.ä. nicht stillschweigend verschluckt werden.
        import traceback

        print(
            f"[TTS /tts_single_sentence] Fehler bei TTS-Aufruf: {e}",
            flush=True,
        )
        print(traceback.format_exc(), flush=True)
        return JSONResponse(
            content={"error": f"TTS-Fehler: {type(e).__name__}: {e}"},
            status_code=500,
        )


@app.post("/add_to_conversation_protocol")
async def add_to_conversation_protocol(request: Request):
    data = await request.json()
    speaker = data.get("speaker")
    text = data.get("text")
    protocol_service.write_to_protocol(speaker, text)
    return {"message": f"Zum Protokoll hinzugefügt: {speaker}"}


# --- STT for Image Annotation (Knowledge Mode) ---
@app.post("/stt_knowledge_annotation")
async def stt_knowledge_annotation(recording: UploadFile = File(...)):
    audio_path = os.path.join("runtime", "temp_audio", "annotation.wav")
    with open(audio_path, "wb") as f:
        content = await recording.read()
        f.write(content)

    if not vad_service.validate_speech_content(audio_path):
        return {"transcription": None, "message": "❌ Keine Sprache erkannt."}

    transcription = stt_service.transcribe_audio(audio_path, frontend_language)

    return {"transcription": transcription, "message": None}


# --- Calculate Embeddings and add Image + Annotation to embeddings.json ---
@app.post("/add_clip_embedding")
async def add_clip_embedding(request: Request):
    """
    Fügt ein neues Bildembedding hinzu (interaktiv aus dem Frontend).
    Erwartet ein JSON mit 'image' (base64), 'title', 'description'.
    """
    try:
        data = await request.json()
        image_data = data.get("image")  # base64
        title = data.get("title")
        description = data.get("description", "")

        if not image_data or not title:
            return JSONResponse(
                content={"error": "Bild und Titel erforderlich."}, status_code=400
            )

        # Speicherort vorbereiten
        image_path = os.path.join("runtime", "temp_images", "snapshot.jpg")

        # Base64 dekodieren und speichern
        header, encoded = image_data.split(",", 1)
        image_bytes = base64.b64decode(encoded)
        image = Image.open(BytesIO(image_bytes))
        image.save(image_path)

        # Embedding hinzufügen
        success = clip_service.add_to_embeddings(image_path, title, description)

        # Embeddings neuladen
        clip_service.data = clip_service.load_embeddings(clip_service.embeddings_file)

        if success:
            return JSONResponse(
                content={"message": "Neues Embedding erfolgreich hinzugefügt"},
                status_code=200,
            )
        else:
            return JSONResponse(
                content={"error": "Fehler beim Hinzufügen des Embeddings"},
                status_code=500,
            )

    except Exception as e:
        return JSONResponse(
            content={"error": f"Serverfehler: {str(e)}"}, status_code=500
        )


# --- Admin Routes ---

@app.get("/admin/config", response_class=HTMLResponse)
async def admin_config_page(request: Request):
    with open("config/config.json") as f:
        current_config = json.load(f)

    # Embedding-Einträge laden
    try:
        with open("data/embeddings/embeddings.json", encoding="utf-8") as f:
            embedding_list = json.load(f)
            embedding_keys = [e.get("title", "Unbenannt") for e in embedding_list]
    except Exception:
        embedding_keys = []

    return admin_templates.TemplateResponse(
        request,
        "config.html",
        {
            "llm_enabled": current_config.get("local", True),
            "stt_enabled": current_config.get("stt_local", True),
            "llm_model": current_config.get("llm_model", "openai/gpt-oss-120b"),
            "tts_voice": current_config.get("tts_voice", "alloy"),
            "embedding_keys": embedding_keys,
        },
    )


# route for updating /config/config.json
@app.post("/admin/update_config")
async def update_config(request: Request):
    form = await request.form()
    current_config = {}
    try:
        with open("config/config.json") as f:
            current_config = json.load(f)
    except Exception:
        pass

    updated_config = {
        "local": "local" in form,
        "stt_local": "stt_local" in form,
        "llm_model": form.get("llm_model", current_config.get("llm_model", "openai/gpt-oss-120b")),
        "tts_voice": form.get("tts_voice", current_config.get("tts_voice", "alloy")),
    }
    with open("config/config.json", "w") as f:
        json.dump(updated_config, f, indent=2)
    return RedirectResponse("/admin/config", status_code=303)


# route for deleting embeddings (visRAG, CLIP) via /admin/config
@app.post("/admin/delete_embedding")
async def delete_embedding(request: Request):
    form = await request.form()
    title_to_delete = form.get("embedding_key")
    embeddings_path = "data/embeddings/embeddings.json"

    try:
        with open(embeddings_path, "r", encoding="utf-8") as f:
            embedding_list = json.load(f)

        new_list = [e for e in embedding_list if e.get("title") != title_to_delete]

        if len(new_list) == len(embedding_list):
            return HTMLResponse("Titel nicht gefunden.", status_code=404)

        with open(embeddings_path, "w", encoding="utf-8") as f:
            json.dump(new_list, f, indent=2, ensure_ascii=False)

        return RedirectResponse("/admin/config?deleted=1", status_code=303)

    except Exception as e:
        print(f"[Fehler beim Löschen]: {e}")
        return HTMLResponse("Löschen fehlgeschlagen.", status_code=500)


# route for editing knowledge stored in /data/knowledge_library/knowledge.txt for CAGs context
@app.get("/admin/edit_cag", response_class=HTMLResponse)
async def edit_cag_page(request: Request):
    cag_path = "data/knowledge_library/knowledge.txt"

    if not os.path.exists(cag_path):
        return HTMLResponse("Wissensdatei nicht gefunden.", status_code=404)

    with open(cag_path, encoding="utf-8") as f:
        knowledge = f.read()

    return admin_templates.TemplateResponse(
        request, "edit_cag.html", {"knowledge": knowledge}
    )


# route for saving new cag knowledge
@app.post("/admin/save_cag")
async def save_cag_knowledge(request: Request):
    form = await request.form()
    updated_text = form.get("knowledge_text")

    try:
        cag_path = "data/knowledge_library/knowledge.txt"
        # clean linebreaks and else to keep txt file clean and formatted
        cleaned = updated_text.replace("\r\n", "\n")  # Windows → Unix-Zeilenenden
        cleaned = "\n".join(line.rstrip() for line in cleaned.split("\n"))
        cleaned = "\n".join([line for line in cleaned.split("\n") if line.strip() != ""])

        with open(cag_path, "w", encoding="utf-8") as f:
            f.write(cleaned)

        return RedirectResponse("/admin/edit_cag?saved=1", status_code=303)

    except Exception as e:
        print("[Fehler beim Speichern von scads.txt]:", e)
        return HTMLResponse("Speichern fehlgeschlagen.", status_code=500)


# --- TTS control ---


@app.post("/stop_tts")
async def stop_tts():
    """Stoppt laufende TTS-Ausgabe."""
    try:
        tts_service.stop_audio()
        return {"message": "TTS gestoppt"}
    except Exception as e:
        return {"error": f"TTS konnte nicht gestoppt werden: {str(e)}"}


#
# --- end of routes ---
#


###############
#
# function(s)
#
###############
# this function is necessary for thread-safe shutdown of the app
@app.on_event("shutdown")
def shutdown_event():
    """Wird beim Beenden der Anwendung aufgerufen."""
    tts_service.shutdown()
    global websocket
    websocket = None


#
# --- end of function(s) ---
#


###############
#
# main
#
###############
HTTPS = True
PORT = 8112

if __name__ == "__main__":
    if HTTPS:
        # Run with HTTPS/SSL
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=PORT,
            ssl_keyfile="./ssl_certificate/key.pem",
            ssl_certfile="./ssl_certificate/cert.pem",
        )
    else:
        uvicorn.run("main:app", host="0.0.0.0", port=PORT)
