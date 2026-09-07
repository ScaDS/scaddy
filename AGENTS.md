# AGENTS.md

Scaddy: tablet-based multi-agent conversational AI for Living Lab tours.
Single-process FastAPI app (`main.py:app`) serving a static SPA frontend plus
speech/vision/LLM services. German is the working language for comments, UI
text, and prompts — keep that convention.

## Commands

No test suite, linter, typechecker, or CI exists. `modules/testing/` holds
manual ad-hoc scripts, not tests — do not assume `pytest` works.

Dependencies are managed with [uv](https://docs.astral.sh/uv/):
`pyproject.toml` declares them, `uv.lock` pins them.

```bash
# Install uv (if not already installed):
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install all dependencies into .venv/ (torch, fastapi, faster-whisper, …):
uv sync --frozen --no-dev

# Start the dev server:
uv run uvicorn main:app --host 0.0.0.0 --port 8112 \
  --ssl-keyfile ssl_certificate/key.pem \
  --ssl-certfile ssl_certificate/cert.pem

# Docker (production/lab). Certs MUST be in ./ssl_certificate/, not ./configs/ssl/
docker-compose build
docker-compose up -d
docker-compose logs -f
docker-compose stop      # use stop, NOT down (down deletes the container)
```

## LLM backend configuration — read this before touching LLM code

All LLM/VLM/TTS calls go to OpenAI-compatible endpoints configured via
`.env` (see `.env.example`). The central configuration lives in
`modules/backend_config.py`.

- `LLM_BASE_URL` — endpoint for chat completions (used by
  `modules/llm/agents_service.py` and `modules/llm/cag_service.py`)
- `VLM_BASE_URL` — endpoint for image captioning/OCR
  (`modules/vision/vlm_service.py`)
- `TTS_BASE_URL` — endpoint for OpenAI-compatible `/v1/audio/speech`
  (`modules/audio/tts_service.py`)
- `STT_API_BASE_URL` — endpoint for remote STT (only if `stt_local` is false)

Voice name and LLM model can be changed at runtime via the admin panel
(`/admin/config`), which edits `config/config.json`.

## Hot-reload vs. restart-required settings

- `config.json["local"]` — hot-reload (read per request in `agents_service.py`).
- `config.json["tts_voice"]` — hot-reload (read per request in `tts_service.py`).
- `config.json["llm_model"]` — hot-reload (read per request).
- `config.json["stt_local"]` — **restart required** (read once at
  `STTService` class-definition time in `modules/audio/stt_service.py`).

## Docker deployment gotchas

- **SSL cert location:** Dockerfile CMD hardcodes `./ssl_certificate/{key,cert}.pem`
  and docker-compose mounts `./ssl_certificate`. Put certs there for Docker; the
  `./configs/ssl/` path is for local dev only.
- **`TORCH_HOME`/`HF_HOME`** are set via `os.environ.setdefault()` in `main.py`
  and `modules/audio/vad_service.py` — they default to `<repo_root>/models` for
  local dev, but respect values set by Docker. docker-compose sets both to
  `/app/runtime/models/{torch,hf}` (mounted via `./runtime:/app/runtime`), so
  silero/whisper/CLIP models persist across container recreations.
- **Port:** Docker uses **8112**. `main.py` hardcodes `PORT = 8112` and
  `HTTPS = True`, but those only affect bare `python main.py`, not Docker.
- **Network:** `scaddy_net` bridge with subnet `192.168.250.0/24` is intentional —
  it avoids collisions with other Docker networks on the host.
- **GPU:** requires NVIDIA Container Toolkit + the
  `nvidia/cuda:12.6.1-cudnn-devel-ubuntu22.04` base image.
- **ALSA/JACK log noise** inside the container is harmless (no sound card). Audio
  processing still works file-based.
- Image is large; never run `docker system prune -a` blindly.

## Architecture

All services are instantiated as module-level singletons in `main.py`.
Editing a service module affects one global instance.

- `modules/audio/` — `vad_service` (Silero-VAD), `stt_service` (faster-whisper
  local or OpenAI API; post-processes misheard "ScaDS"/"Scaddy" names),
  `tts_service` (OpenAI-compatible TTS).
- `modules/llm/` — `agents_service` (multi-agent pipeline: main conversation
  agent + CAG knowledge agent + sentence formatter agent), `cag_service`
  (Cache-Augmented Generation — knowledge base as context, simplified CAG).
- `modules/vision/` — `clip_service` (visRAG similarity vs
  `data/embeddings/embeddings.json`; thresholds in `main.py`: <0.60 unknown,
  0.60–0.799 unsure, ≥0.80 match — heuristic, tunable), `vlm_service` (image
  description + OCR via OpenAI-compatible VLM endpoint).
- `modules/protocol/` — `conversation_protocol` (JSON files under
  `runtime/protocol/`).
- `modules/search/` — Perplexica integration; **not wired into the live agent**.

Main flow: `POST /audio_enabled_conversation` → VAD → STT → (CLIP + VLM if
image) → LLM → WebSocket push → client requests TTS per sentence via
`/tts_single_sentence`.

Full module map + endpoint table: `documentation/backend.md`.
