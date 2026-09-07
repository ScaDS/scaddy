# Contributing to Scaddy

Thank you for your interest in contributing! This guide covers the basics.

## Getting Started

### Prerequisites

- Python 3.10 or 3.11
- [uv](https://docs.astral.sh/uv/) (fast Python package manager)
- Docker + Docker Compose (for containerized deployment)
- NVIDIA GPU with CUDA 12.x support (for local STT and CLIP)
- NVIDIA Container Toolkit (for GPU access in Docker)

### Local Development Setup

```bash
# 1. Clone the repository
git clone https://github.com/scads/scaddy.git
cd scaddy

# 2. Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Install all dependencies into .venv/
#    (torch, fastapi, faster-whisper, … — pinned via uv.lock)
uv sync --frozen --no-dev

# 4. Set up environment variables
cp .env.example .env
# Edit .env with your API keys and endpoints

# 5. Generate a self-signed SSL certificate
mkdir -p ssl_certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl_certificate/key.pem \
  -out ssl_certificate/cert.pem

# 6. Start the development server
uv run uvicorn main:app --host 0.0.0.0 --port 8112 \
  --ssl-keyfile ssl_certificate/key.pem \
  --ssl-certfile ssl_certificate/cert.pem
```

### Docker Development

```bash
# Build and start
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop (preserves container for quick restart)
docker-compose stop

# Destroy (removes container, keeps volumes)
docker-compose down
```

## Code Style

- **Python:** Follow [PEP 8](https://peps.python.org/pep-0008/).
  No formatter/linter is enforced (yet), but consistency is appreciated.
- **JavaScript/Vue:** Follow the existing patterns in `frontend/static/index.html`.
  No build step — edit files directly.
- **Language:** The codebase uses a mix of German and English comments.
  New code should use English for broader accessibility.
  UI strings should be added to `translations.js` for i18n support.

## Making Changes

1. **Fork** the repository on GitHub
2. **Clone** your fork locally
3. **Create a branch** for your feature:
   ```bash
   git checkout -b feature/my-new-feature
   ```
4. **Make your changes** and test them:
   ```bash
   # Syntax check
   python -m py_compile main.py modules/**/*.py

   # Config validation
   python -c "import json; json.load(open('config/config.json'))"

   # Docker build test (if Docker-related changes)
   docker-compose build
   ```
5. **Commit** your changes with a clear message:
   ```bash
   git commit -m "Add feature: description of what it does"
   ```
6. **Push** to your fork:
   ```bash
   git push origin feature/my-new-feature
   ```
7. **Open a Pull Request** on the main repository

## Pull Request Guidelines

- Keep PRs focused — one feature or fix per PR
- Include a clear description of what changed and why
- Test your changes locally before submitting
- Update documentation if you change behavior
- Add new UI strings to `translations.js`

## Reporting Issues

When [opening an issue](https://github.com/scads/scaddy/issues/new), please include:

1. **Description:** What happened vs. what you expected
2. **Environment:** OS, Docker version, GPU model, Python version
3. **Steps to reproduce:** Minimal example to trigger the issue
4. **Logs:** Relevant output from `docker-compose logs` or console
5. **Screenshots:** If the issue is visual (UI bugs, image processing errors)

## License

By contributing to this project, you agree that your contributions will be
licensed under the [MIT License](LICENSE).
