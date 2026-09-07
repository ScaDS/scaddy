FROM nvidia/cuda:12.6.1-cudnn-devel-ubuntu22.04

# System dependencies
# - ffmpeg: audio/video processing (WAV conversion, format detection)
# - libsndfile1: sound file I/O backend for the SoundFile Python package
# - libasound2: ALSA audio (harmless ALSA/JACK log noise in container)
# - libgl1-mesa-glx: OpenGL/Mesa for image processing (PIL/CLIP)
# - build-essential: C/C++ compilation toolchain (gcc for building native extensions)
# - portaudio19-dev: PortAudio development headers (required to compile PyAudio)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    libasound2 \
    libgl1-mesa-glx \
    build-essential \
    git \
    curl \
    wget \
    portaudio19-dev \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package manager)
# See: https://docs.astral.sh/uv/guides/integration/docker/
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency files first (for Docker layer caching)
COPY pyproject.toml uv.lock ./

# Install Python dependencies with uv
# --frozen: use uv.lock exactly as-is (no re-resolution)
# --no-dev: skip development dependencies (pytest, ruff)
# --no-install-project: only install dependencies, not the project itself
#   (we just want the packages, not an installed 'scaddy' distribution)
RUN uv sync --frozen --no-dev --no-install-project

# Copy application code
COPY . /app

# Activate the uv-managed virtual environment
# (all subsequent commands use /app/.venv/bin/uvicorn etc.)
ENV PATH="/app/.venv/bin:$PATH"

# Set model cache directory (models are downloaded at first run and cached here)
# This directory should be mounted as a Docker volume for persistence.
ENV TORCH_HOME=/app/runtime/models/torch

# Expose HTTPS port
EXPOSE 8112

# Start the application with uvicorn
# SSL certificates must be mounted at /app/ssl_certificate/
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8112", "--ssl-keyfile", "./ssl_certificate/key.pem", "--ssl-certfile", "./ssl_certificate/cert.pem"]
