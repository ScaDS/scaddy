# Security Policy

## No Warranty, No Support

This software is provided "as is", without warranty of any kind, express or
implied. The maintainers provide no support and accept no liability for any
damages arising from the use of this software.

## Known Security Limitations

### Admin Panel Has No Authentication

The admin panel (`/admin/config`) and all admin endpoints are **not
authenticated**. Anyone with network access to the Scaddy server can:

- Read and modify the configuration (`config/config.json`)
- Read and modify the knowledge base (`data/knowledge_library/`)
- Delete visual embeddings (visRAG data)
- Read conversation protocols

**Mitigation:** Do not expose the Scaddy server directly to the public
internet. Use one of these approaches:

1. **Firewall:** Restrict access to trusted networks (VPN, LAN) only
2. **Reverse Proxy:** Put a reverse proxy (nginx, Caddy, Traefik) with
   Basic Auth or OAuth2 in front of the application
3. **Network Segmentation:** Run Scaddy in an isolated Docker network
   (default behavior in `docker-compose.yml`)

### CORS Is Set to Allow All Origins

```python
allow_origins=["*"]
```

This is necessary for the tablet frontend to connect from any network.
However, it means any website can make API calls to your Scaddy instance
if the user has the page open in the same browser session.

### Secrets in Environment Variables

API keys and other secrets are stored in `.env` files and passed as
environment variables. Ensure:

- `.env` is in `.gitignore` (it is by default)
- `.env` is in `.dockerignore` (it is by default)
- You never commit `.env` files to version control
- Docker images built from this repository do not contain `.env`

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Instead, use GitHub's private vulnerability reporting:

1. Go to the repository on GitHub
2. Click the "Security" tab
3. Click "Report a vulnerability"
4. Follow the prompts to submit privately

### What to Include

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### Response Timeline

The maintainers will acknowledge receipt within 7 days. There is no
guaranteed fix timeline as this is a research project without dedicated
security resources.

---

**TL;DR:** This is a research project for an internal Living Lab deployment.
It is not hardened for public internet exposure. Use firewalls and reverse
proxies.
