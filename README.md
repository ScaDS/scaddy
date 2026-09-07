# Scaddy — Multi-Agent Conversational AI for Living Lab Tours

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue)](https://www.docker.com/)

Scaddy is a tablet-based, multi-agent conversational AI designed for guided
tours in Living Lab environments. It combines:

- **Voice input** via faster-whisper (local) or OpenAI Whisper API (remote)
- **Image recognition** via CLIP embeddings (visRAG — Visual Retrieval-Augmented Generation)
- **Multi-agent LLM pipeline** with a main conversation agent, a sentence
  formatter agent, and a CAG (Cache-Augmented Generation) knowledge agent
- **Text-to-speech** via any OpenAI-compatible TTS endpoint
- **VLM (Vision Language Model)** for image description and OCR

> 📖 **Read the blog post:**
> [Scaddy: Multimodal Conversational AI at Living Lab Leipzig](https://scads.ai/scaddy-multimodal-conversational-ai-at-living-lab-leipzig/)

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Tablet Frontend                          │
│  (Vue.js 3 SPA — no build step, served as static files)         │
│  Microphone → Audio Recording → WebSocket → Backend             │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                      FastAPI Backend (main.py)                    │
│                                                                   │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌──────────────────┐  │
│  │   VAD   │→ │   STT   │→ │   LLM   │→ │        TTS       │  │
│  │ Silero  │  │ faster- │  │ Multi-  │  │ OpenAI-compatible │  │
│  │   VAD   │  │ whisper │  │ Agent   │  │ /audio/speech     │  │
│  └─────────┘  └─────────┘  └─────────┘  └──────────────────┘  │
│                                    │                             │
│                          ┌─────────▼─────────┐                  │
│                          │    CAG Agent      │                  │
│                          │ (knowledge base   │                  │
│                          │  via context)     │                  │
│                          └───────────────────┘                  │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                   Vision Pipeline (visRAG)               │    │
│  │  Image → CLIP Embedding → Similarity Search vs Database │    │
│  │         + VLM (image description + OCR)                  │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### Multi-Agent Pipeline

The multi-agent LLM pipeline consists of three agents working together:

1. **Main Agent (ScaddyImageBot):** Handles the main conversation. It
   receives the transcribed user input (plus optional image description),
   decides whether to use the CAG knowledge agent, and generates the
   conversational response.

2. **CAG Agent (cag_tool):** Provides domain-specific knowledge from a
   pre-loaded knowledge base (Cache-Augmented Generation). The main agent
   can invoke this tool when the user asks about the Living Lab, research
   projects, or other domain-specific topics.

3. **Formatter Agent (SentenceFormatterAgent):** Reformats the LLM's response
   by inserting `#pause#` markers at natural sentence boundaries. This enables
   the TTS engine to produce speech with natural pauses between sentences.

### Vision Pipeline (visRAG)

The vision pipeline processes images in two ways:

1. **CLIP Similarity Search:** The image is converted into a CLIP embedding
   and compared against a pre-built embeddings database. If a match is found
   (similarity ≥ 0.80), the associated title and description are used.

2. **VLM (Vision Language Model):** The image is sent to a VLM endpoint
   (default: `alias-vision`) which generates a description including OCR
   (text extraction from the image).

Both results are combined into an `image_description` that is passed to the
main conversation agent.

### Audio Pipeline

1. **VAD (Voice Activity Detection):** Silero VAD checks if the recorded
   audio contains speech. If not, the request is discarded.

2. **STT (Speech-to-Text):** faster-whisper transcribes the audio locally
   (GPU-accelerated). Alternatively, the OpenAI Whisper API can be used.

3. **TTS (Text-to-Speech):** The response is converted to speech via an
   OpenAI-compatible `/audio/speech` endpoint (default: OmniVoice on
   `llm.scads.ai`).

## Quick Start (Docker)

### Prerequisites

- Docker + Docker Compose
- NVIDIA GPU with CUDA 12.x support
- NVIDIA Container Toolkit (for GPU access in Docker)
- ~6 GB free disk space (Docker image) + ~2 GB (models)

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/scads/scaddy.git
cd scaddy

# 2. Set up environment variables
cp .env.example .env
# Edit .env with your API keys and endpoint URLs

# 3. Generate a self-signed SSL certificate (required for HTTPS)
mkdir -p ssl_certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl_certificate/key.pem \
  -out ssl_certificate/cert.pem

# 4. Build and start
docker-compose up -d --build

# 5. Access the application
# Main UI: https://localhost:8112
# Admin Panel: https://localhost:8112/admin/config
```

### First Steps

1. Open `https://localhost:8112` in your browser
2. Accept the self-signed certificate warning
3. Allow microphone access when prompted
4. Click "Talk to Scaddy" and ask a question
5. Try the vision mode: take a photo and ask about it

### Docker Setup Details

**Base Image:** `nvidia/cuda:12.6.1-cudnn-devel-ubuntu22.04` (~8 GB)
- CUDA 12.6 runtime + cuDNN development libraries
- Required for GPU-accelerated faster-whisper and CLIP

**What Gets Installed:**

| Category | Components |
|----------|-----------|
| System (apt) | `ffmpeg`, `libsndfile1`, `libasound2`, `libgl1-mesa-glx`, `build-essential`, `portaudio19-dev`, `git`, `curl`, `wget`, `python3`, `python3-pip` |
| AI/ML (pip) | `torch 2.7.1+cu126`, `transformers`, `faster-whisper`, `silero-vad`, `openai` |
| Web (pip) | `fastapi`, `uvicorn`, `starlette`, `python-multipart` |
| Audio (pip) | `pydub`, `pyaudio` |
| Vision (pip) | `pillow`, `numpy` |

**Models Downloaded at First Run:**

| Model | Size | Purpose |
|-------|------|---------|
| Silero VAD v5 | ~2 MB | Voice Activity Detection |
| faster-whisper "medium" | ~1.5 GB | Local speech-to-text |
| CLIP ViT-B/32 | ~600 MB | Visual embeddings (visRAG) |

**GPU Requirements:**

| Component | VRAM |
|-----------|------|
| faster-whisper "medium" | ~3 GB |
| CLIP ViT-B/32 | ~0.5-1 GB |
| Silero VAD | minimal |
| **Total** | **~4-5 GB** |

**Volumes:**

| Host | Container | Purpose |
|------|-----------|---------|
| `./data` | `/app/data` | Knowledge base, embeddings, images |
| `./config` | `/app/config` | Runtime configuration |
| `./runtime` | `/app/runtime` | Model cache, temp files, protocols |
| `./ssl_certificate` | `/app/ssl_certificate` | SSL certificates |
| `./frontend/static` | `/app/frontend/static` | Frontend files |
| `./admin/templates` | `/app/admin/templates` | Admin panel templates |

**Ports:**
- `8112` — HTTPS (uvicorn with SSL)

## Configuration

All configuration is done via environment variables (`.env` file) and
runtime configuration (`config/config.json`).

### Environment Variables (`.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_BASE_URL` | `https://llm.scads.ai/v1` | Base URL for LLM (chat) requests |
| `LLM_API_KEY` | *(from `SCADS_AI_HPC_API_KEY`)* | API key for LLM endpoint |
| `LLM_MODEL` | `openai/gpt-oss-120b` | Model name for LLM |
| `VLM_BASE_URL` | *(same as `LLM_BASE_URL`)* | Base URL for VLM (vision) requests |
| `VLM_API_KEY` | *(same as `LLM_API_KEY`)* | API key for VLM endpoint |
| `VLM_MODEL` | `alias-vision` | Model name for VLM |
| `TTS_BASE_URL` | `https://llm.scads.ai/v1` | Base URL for TTS requests |
| `TTS_API_KEY` | *(from `SCADS_AI_HPC_API_KEY`)* | API key for TTS endpoint |
| `TTS_MODEL` | `OmniVoice` | Model name for TTS |
| `TTS_VOICE` | `alloy` | Voice name for TTS |
| `STT_API_BASE_URL` | `https://api.openai.com/v1` | Base URL for STT API (only when `STT_LOCAL=false`) |
| `STT_API_KEY` | *(from `OPENAI_API_KEY`)* | API key for STT API (only when `STT_LOCAL=false`) |
| `STT_API_MODEL` | `whisper-1` | Model name for STT API |
| `WHISPER_MODEL_SIZE` | `medium` | faster-whisper model size (`tiny`/`base`/`small`/`medium`/`large-v3`) |
| `WHISPER_DEVICE` | `cuda` | Device for faster-whisper |
| `WHISPER_COMPUTE_TYPE` | `float16` | Compute type for faster-whisper |
| `CLIP_MODEL` | `openai/clip-vit-base-patch32` | CLIP model name (HuggingFace format) |
| `CLIP_DEVICE` | `cuda` | Device for CLIP |

### Runtime Configuration (`config/config.json`)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `local` | bool | `true` | Use local LLM endpoint (vs. OpenAI API) |
| `stt_local` | bool | `true` | Use local faster-whisper (vs. OpenAI Whisper API) |
| `llm_model` | str | `openai/gpt-oss-120b` | Model name (overrides `LLM_MODEL` env var) |
| `tts_voice` | str | `alloy` | Voice name for TTS (overrides `TTS_VOICE` env var) |

**Note:** `stt_local` is read once at application startup. Changing it
requires a container restart. All other settings are hot-reloaded (read
on every request).

## Backend Configuration Examples

### Example 1: ScaDS.AI Living Lab (Default)

```bash
# .env
LLM_BASE_URL=https://llm.scads.ai/v1
LLM_API_KEY=your_scads_api_key
LLM_MODEL=openai/gpt-oss-120b

VLM_BASE_URL=https://llm.scads.ai/v1
VLM_MODEL=alias-vision

TTS_BASE_URL=https://llm.scads.ai/v1
TTS_MODEL=OmniVoice
TTS_VOICE=alloy
```

### Example 2: OpenAI (Remote)

```bash
# .env
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4o

VLM_BASE_URL=https://api.openai.com/v1
VLM_API_KEY=sk-...
VLM_MODEL=gpt-4o

TTS_BASE_URL=https://api.openai.com/v1
TTS_API_KEY=sk-...
TTS_MODEL=tts-1
TTS_VOICE=alloy

STT_API_BASE_URL=https://api.openai.com/v1
STT_API_KEY=sk-...
STT_API_MODEL=whisper-1
```

### Example 3: Fully Local (llama.cpp + Kokoro-FastAPI)

```bash
# .env — assumes llama.cpp llama-server on :8080 and Kokoro-FastAPI on :8880
LLM_BASE_URL=http://llama-server:8080/v1
LLM_API_KEY=none
LLM_MODEL=qwen3-4b-instruct

VLM_BASE_URL=http://llama-server:8080/v1
VLM_MODEL=qwen3-vl-4b-instruct

TTS_BASE_URL=http://kokoro:8880/v1
TTS_API_KEY=none
TTS_MODEL=kokoro
TTS_VOICE=af_bella
```

**Note on local LLMs:** Tool calling (CAG agent) may not work reliably with
small local models. Models need to emit proper OpenAI-style `tool_calls` JSON.
Test with your specific model.

### Example 4: LM Studio (Local Desktop)

```bash
# .env — assumes LM Studio running on :1234
LLM_BASE_URL=http://host.docker.internal:1234/v1
LLM_API_KEY=lm-studio
LLM_MODEL=your-loaded-model-name
```

## Admin Panel

Access at `https://localhost:8112/admin/config`:

- **LLM Model:** Text input for the model name (hot-reload, no restart needed)
- **STT Mode:** Toggle between local faster-whisper and OpenAI Whisper API
  (⚠️ **restart required**)
- **TTS Voice:** Text input for the voice name (hot-reload)
- **Embeddings:** View and delete visual embeddings (visRAG)
- **Knowledge:** Edit the CAG knowledge base (hot-reload)

**Important:** The admin panel has **no authentication**. Do not expose it
to the public internet. See `SECURITY.md` for details.

## Knowledge Base (CAG)

The knowledge base is a plain text file at
`data/knowledge_library/knowledge.txt`. Edit it via the admin panel
(`/admin/edit_cag`) or directly.

### How to Add CAG Knowledge

1. **Via Admin Panel (recommended):**
   - Open `https://localhost:8112/admin/config`
   - Click "✏️ View & Edit Knowledge"
   - Write or paste your domain knowledge into the editor
   - Click "💾 Save" — the new content is active immediately
     (no restart required, the file is re-read on each conversation turn)

2. **Via Filesystem:**
   - Edit `data/knowledge_library/knowledge.txt` directly
   - The change takes effect on the next conversation turn

3. **Example:** For ScaDS.AI deployments, copy the content from
   `data/knowledge_library/scads_knowledge_example.txt` into the editor
   (or into `knowledge.txt`) to get started with curated ScaDS knowledge.

**Format:** Free-form text. Structure with headers and lists for better
LLM comprehension. The entire file is loaded into the context window
when the `cag_tool` is invoked.

**Recommended structure:**

```markdown
## Organization
- Name, locations, founding year
- Mission and goals
- Team structure and roles

## Research Areas
- Applied AI and Big Data
- Data integration and data quality
- Privacy-preserving machine learning

## Facilities / Living Lab
- Description of the Living Lab
- Available demonstrations and exhibits
- Visitor information (opening hours, contact)

## FAQ
- Common questions and their answers
```

**Size limit:** Keep it under ~50,000 characters (roughly 12,500 tokens)
to ensure it fits in the context window alongside conversation history.

## Vision Knowledge (visRAG)

The vision knowledge base consists of:

1. **Embeddings Database** (`data/embeddings/embeddings.json`):
   A JSON array of objects, each containing:
   - `title`: Human-readable name of the object
   - `description`: Detailed description of the object
   - `embedding`: CLIP embedding vector (512 dimensions)
   - `image_path`: Path to the reference image

2. **Reference Images** (`data/embeddings/images/`):
   The original images used to generate the embeddings.

### How to Add Visual Knowledge

1. Open the Scaddy web interface
2. Click the camera icon to enter vision mode
3. Take a photo of the object you want to teach Scaddy
4. Click "Add knowledge" (plus icon)
5. Provide a title and description for the object
6. Click "Save" — the embedding is calculated and stored

**Note:** The embeddings database is empty by default. You need to
add visual knowledge for objects in your Living Lab before the
vision mode can recognize them.

## Local Development (without Docker)

Scaddy uses [uv](https://docs.astral.sh/uv/) as its Python package manager.
Dependencies are declared in `pyproject.toml` and locked in `uv.lock`
(PyTorch comes from the official CUDA 12.6 wheel index).

```bash
# Prerequisites: Python 3.10+, CUDA-capable GPU, ffmpeg installed, uv installed
# Install uv:  curl -LsSf https://astral.sh/uv/install.sh | sh

# 1. Install all dependencies into .venv/ (torch, fastapi, faster-whisper, …)
uv sync --frozen --no-dev

# 2. Set up environment
cp .env.example .env
# Edit .env

# 3. Generate SSL certificate
mkdir -p ssl_certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl_certificate/key.pem \
  -out ssl_certificate/cert.pem

# 4. Start the server (uses the uv-managed virtual environment)
uv run uvicorn main:app --host 0.0.0.0 --port 8112 \
  --ssl-keyfile ssl_certificate/key.pem \
  --ssl-certfile ssl_certificate/cert.pem
```

## Project Structure

```
scaddy/
├── main.py                          # FastAPI app, routes, WebSocket
├── config/
│   ├── config.json                  # Runtime configuration (hot-reload)
│   └── ssl/                         # SSL certificates (gitignored)
├── data/
│   ├── embeddings/                  # CLIP embeddings for visRAG
│   │   ├── embeddings.json          # Embedding vectors + metadata
│   │   └── images/                  # Reference images for visRAG
│   └── knowledge_library/           # CAG knowledge base
│       └── knowledge.txt            # Active knowledge base
├── modules/
│   ├── backend_config.py            # Central backend configuration
│   ├── audio/
│   │   ├── stt_service.py           # Speech-to-Text (faster-whisper / API)
│   │   ├── tts_service.py           # Text-to-Speech (OpenAI-compatible)
│   │   └── vad_service.py           # Voice Activity Detection (Silero VAD)
│   ├── llm/
│   │   ├── agents_service.py        # Multi-agent LLM pipeline
│   │   └── cag_service.py           # CAG knowledge service
│   ├── vision/
│   │   ├── clip_service.py          # CLIP embeddings (visRAG)
│   │   └── vlm_service.py           # Vision Language Model (VLM)
│   ├── protocol/
│   │   └── conversation_protocol.py # Conversation history management
│   ├── search/
│   │   └── search_service.py        # Perplexica integration (optional)
│   └── testing/                     # Manual test scripts (not a test suite)
├── frontend/
│   └── static/
│       ├── index.html               # Vue.js 3 SPA (no build step)
│       ├── index.css                # Custom CSS (no framework)
│       └── translations.js          # i18n strings (DE/EN)
├── admin/
│   └── templates/
│       ├── config.html              # Admin panel configuration page
│       └── edit_cag.html            # Knowledge base editor
├── docker-compose.yml               # Docker Compose configuration
├── dockerfile                       # Docker build instructions (uses uv)
├── pyproject.toml                   # Project metadata + dependencies (uv)
├── uv.lock                          # Locked dependency versions (uv)
├── LICENSE                          # MIT License
├── ACKNOWLEDGMENTS.md               # Detailed acknowledgments
├── SECURITY.md                      # Security policy and limitations
├── CONTRIBUTING.md                  # How to contribute
├── CITATION.cff                     # Citation metadata (for GitHub)
└── NOTICE                           # Third-party license notices
```

## Acknowledgments

Scaddy is built on many excellent open-source projects:

- **[faster-whisper](https://github.com/SYSTRAN/faster-whisper)** (MIT) — Local speech-to-text
- **[CLIP (OpenAI)](https://github.com/openai/CLIP)** (MIT) — Visual embeddings for visRAG
- **[Silero VAD](https://github.com/snakers4/silero-vad)** (MIT) — Voice Activity Detection
- **[Transformers](https://github.com/huggingface/transformers)** (Apache-2.0) — Model loading and inference
- **[PyTorch](https://github.com/pytorch/pytorch)** (BSD-3-Clause) — Deep learning framework
- **[FastAPI](https://github.com/tiangolo/fastapi)** (MIT) — Web framework
- **[Vue.js 3](https://github.com/vuejs/core)** (MIT) — Frontend framework

See [ACKNOWLEDGMENTS.md](ACKNOWLEDGMENTS.md) for the complete list with
licenses and purposes, and [NOTICE](NOTICE) for third-party license notices.

## Contributors

Scaddy was developed at the [ScaDS.AI Dresden/Leipzig](https://www.scads.ai)
Living Lab by:

- **[Oliver Welz](https://scads.ai/event/meetup)** — Project lead, architecture, multi-agent pipeline, features
- **Philipp Schott** — Backend, features, agents
- **Gregor Wolf** — Frontend, vision pipeline, agents, testing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for how to
get started.

## Research Context

This software was developed as part of the [ScaDS.AI Dresden/Leipzig](https://www.scads.ai)
Living Lab, funded funded by the Federal Ministry of Research, Technology and Space of Germany and the Free State of Saxony.

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

## Citation

If you use Scaddy in your research, please cite it as:

```bibtex
@software{scaddy2025,
  author = {Welz, Oliver and Schott, Philipp and Wolf, Gregor},
  title = {Scaddy: Multi-Agent Conversational AI for Living Lab Tours},
  year = {2025},
  publisher = {GitHub},
  url = {https://github.com/scads/scaddy}
}
```
