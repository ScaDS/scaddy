# Acknowledgments

Scaddy is built on the shoulders of many excellent open-source projects.
This file acknowledges all libraries, frameworks, models, and infrastructure
components that make Scaddy possible.

## Core Dependencies

| Project | License | Purpose |
|---------|---------|---------|
| [FastAPI](https://github.com/tiangolo/fastapi) | MIT | Web framework and REST API |
| [Uvicorn](https://github.com/encode/uvicorn) | BSD-3-Clause | ASGI web server |
| [Pydantic](https://github.com/pydantic/pydantic) | MIT | Data validation and settings |
| [python-multipart](https://github.com/python-openai/python-multipart) | Apache-2.0 | Multipart form data parsing |
| [OpenAI Python SDK](https://github.com/openai/openai-python) | Apache-2.0 | OpenAI-compatible API client |
| [requests](https://github.com/psf/requests) | Apache-2.0 | HTTP client |
| [python-dotenv](https://github.com/theskumar/python-dotenv) | BSD-3-Clause | Environment variable loading |

## AI/ML Libraries

| Project | License | Purpose |
|---------|---------|---------|
| [PyTorch](https://github.com/pytorch/pytorch) | BSD-3-Clause | Deep learning framework |
| [Transformers](https://github.com/huggingface/transformers) | Apache-2.0 | CLIP model loading and inference |
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | MIT | Speech-to-text (local) |
| [CTranslate2](https://github.com/OpenNMT/CTranslate2) | MIT | Inference engine for faster-whisper |
| [Silero VAD](https://github.com/snakers4/silero-vad) | MIT | Voice Activity Detection |
| [CLIP (OpenAI)](https://github.com/openai/CLIP) | MIT | Visual embeddings (visRAG) |
| [Tokenizers](https://github.com/huggingface/tokenizers) | Apache-2.0 | Fast tokenization for Transformers |

## Audio Processing

| Project | License | Purpose |
|---------|---------|---------|
| [PyAudio](https://people.csail.mit.edu/hubert/pyaudio/) | MIT | Audio I/O (microphone/speaker) |
| [Pydub](https://github.com/jiaaro/pydub) | MIT | Audio format conversion and manipulation |
| [Resampy](https://github.com/bmcfee/resampy) | ISC | High-quality audio resampling |
| [SoundFile](https://github.com/bastibe/python-soundfile) | BSD-3-Clause | Audio file I/O (via libsndfile) |
| [NumPy](https://github.com/numpy/numpy) | BSD-3-Clause | Numerical computing (audio arrays) |

## Frontend

| Project | License | Purpose |
|---------|---------|---------|
| [Vue.js 3](https://github.com/vuejs/core) | MIT | Reactive frontend framework (via CDN) |
| [Font Awesome 6](https://github.com/FortAwesome/Font-Awesome) | CC-BY-4.0 (icons) / MIT (code) | Icon library |

## Vision

| Project | License | Purpose |
|---------|---------|---------|
| [Pillow](https://github.com/python-pillow/Pillow) | HPND/MIT-CMU | Image loading, processing, format conversion |

## Infrastructure

| Project | License | Purpose |
|---------|---------|---------|
| [NVIDIA CUDA Docker Images](https://hub.docker.com/r/nvidia/cuda) | [NVIDIA Deep Learning Container License](https://developer.nvidia.com/ngc/nvidia-deep-learning-container-license) | Base image with CUDA 12.6 + cuDNN |
| [Docker](https://www.docker.com/) | Apache-2.0 | Containerization platform |
| [NVIDIA Container Toolkit](https://github.com/NVIDIA/nvidia-container-toolkit) | Apache-2.0 | GPU support for Docker containers |

## AI Models Used

| Model | License | Purpose |
|-------|---------|---------|
| [faster-whisper "medium"](https://huggingface.co/SYSTRAN/faster-whisper-medium) | MIT (code) / Apache-2.0 (OpenAI Whisper model) | Local speech-to-text |
| [CLIP ViT-B/32](https://huggingface.co/openai/clip-vit-base-patch32) | MIT | Visual embeddings for visRAG |
| [Silero VAD v5](https://github.com/snakers4/silero-vad) | MIT | Voice Activity Detection |
| [OmniVoice](https://llm.scads.ai/status/) | Proprietary (ScaDS.AI) | Text-to-speech (remote, via llm.scads.ai) |
| [GPT-OSS-120B](https://llm.scads.ai/status/) | Open-source (OpenAI) | LLM (remote, via llm.scads.ai) |
| [Alias-Vision (Gemma-4-26B)](https://llm.scads.ai/status/) | Open-source (Google) | VLM (remote, via llm.scads.ai) |

## System Libraries (via apt in Docker)

| Library | License | Purpose |
|---------|---------|---------|
| ffmpeg | GPL-2.0+ / LGPL-2.1+ (Debian build) | Audio/video processing, format conversion |
| libsndfile1 | LGPL-2.1 | Sound file I/O backend for SoundFile |
| libasound2 | LGPL-2.1 | ALSA audio library (harmless container log noise) |
| libgl1-mesa-glx | MIT (Mesa) | OpenGL/Mesa for image processing |
| portaudio19-dev | MIT | PortAudio development files for PyAudio compilation |
| build-essential | GPL (gcc) / GPL-2.0 (binutils) | C/C++ compilation toolchain |
| git | GPL-2.0 | Version control system |
| curl | MIT-like (curl license) | HTTP client (for healthchecks) |
| wget | GPL-3.0 | HTTP file download utility |

## Research Context

This software was developed as part of the [ScaDS.AI Dresden/Leipzig](https://www.scads.ai)
Living Lab, funded by the German Federal Ministry of Education and Research (BMBF)
and the Free State of Saxony.

## Special Thanks

- The [ScaDS.AI](https://www.scads.ai) team for infrastructure, research context, and support:
Center for Scalable Data Analytics and Artificial Intelligence (ScaDS.AI) Dresden/Leipzig, Universität Leipzig, Germany
- The open-source community for building and maintaining the incredible tools
  that make projects like this possible
- All contributors who have helped improve Scaddy

*We hereby acknowledge the financial support by the Federal Ministry of Research, Technology and Space of Germany and by Sächsische Staatsministerium für Wissenschaft, Kultur und Tourismus in the programme Center of Excellence for AI-research „Center for Scalable Data Analytics and Artificial Intelligence Dresden/Leipzig“, project identification number: ScaDS.AI*

---

If we've missed acknowledging your project, please [open an issue](https://github.com/scads/scaddy/issues)
so we can add proper attribution.
