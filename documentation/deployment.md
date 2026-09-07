# Deployment Guide – Scaddy Chatbot (Docker)

## 1. Prerequisites

* Docker and Docker Compose installed ([Install Docker](https://docs.docker.com/get-docker/))
* Access to the GitHub repository (via SSH or HTTPS)

---

## 2. Clone the Project

```sh
git clone https://github.com/scads/scaddy.git
cd scaddy
```

---

## 3. Create SSL Certificate

Check "openssl" with:

```sh
openssl version
```
If necessary install openssl. (see README, '1.1 Prerequisites').

Add a folder "ssl_certificate" to the root of the cloned repo (folder tagged in .gitignore).
(Yes, you can also change to ./configs/ssl to use the already existing certificates; change the path maybe in the 'docker-compose.yml')
Generate a self-signed SSL certificate (without password) if not already present:

```sh
openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
  -keyout ssl_certificate/key.pem \
  -out ssl_certificate/cert.pem \
  -subj "/CN=localhost"
```

* Certificates are stored in the `ssl_certificate/` folder.
* **Important:** Only create the certificate once and never commit it to Git.
* **Warning:** The `-days 3650` option creates a certificate valid for 10 years — adjust if needed.
* `-nodes` means no password is required for using the self-signed certificate.

---

## 4. Create `.env` File

In the project root, create a `.env` file (do not commit to the repo!) with the following content:

```ini
SCADS_AI_HPC_API_KEY=your_scads_api_key
```

> Adjust the value according to your environment and the APIs/services you are using.

---

## 5. Build the Backend

```sh
docker-compose build
```

---

## 6. Start the Backend

```sh
docker-compose up
```

* The service is now available at [https://localhost:8112](https://localhost:8112).
* You may need to accept the “insecure certificate” warning in your browser — this is because it’s self-signed.
* Logs will appear in the terminal.

**To run in the background:**

```sh
docker-compose up -d
```

**View logs:**

```sh
docker-compose logs -f
```

---

## 7. Stop the Backend

```sh
docker-compose stop
```

* **Note:**
  Always use `docker-compose stop` to halt the containers so they are **not deleted**.
  `docker-compose down` will stop **and delete** the container!

---

## 8. Notes / Good to Know

* **Certificate** and **.env** should **never** be committed to the repository.
* All changes to mounted files are immediately visible inside the container.
* If you need to rebuild the image (after code changes), run:

  ```sh
  docker-compose build
  ```

---

## Quick Fixes

* **Missing Keys:** Check the `.env` file.
* **SSL Errors:** Ensure the certificate is correctly created and mounted.
* **Port Already in Use:** Check if another service is using the port (e.g., `lsof -i :8112`).

---

**To stop:**

```sh
docker-compose stop
```

**Done!**
Scaddy now runs inside a Docker container with all volumes and environment variables correctly mounted.
It can be easily transferred or redeployed.

**Questions or Issues?**
Check the Troubleshooting section, read the README, review the logs, or ask the team!

---

# Troubleshooting & Lessons Learned – Deployment (CUDA, Audio, Docker/WSL, Python)

This section summarizes common issues, causes, and solutions related to CUDA, Docker, audio, Python, and more during deployment.
Ideal as a reference for the team or future setups.

---

## 1. GPU & CUDA Issues in Docker

**Symptoms**

* `nvidia-smi` works on the host but **not inside the container**
* CUDA not found, AI models not running on GPU

**Causes & Solutions**

* **Host:** Ensure the latest NVIDIA drivers are installed.
* **docker-compose.yml:**

  * For newer Compose versions:

    ```yaml
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    ```
  * For older Compose versions:

    ```yaml
    runtime: nvidia
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
    ```
* **Image:**
  Always use a CUDA+cuDNN base image, e.g.
  `FROM nvidia/cuda:12.6.0-cudnn8-devel-ubuntu20.04`
* Install **NVIDIA Container Toolkit**:
  Guide: [NVIDIA Container Toolkit Install Guide](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)

---

## 2. cuDNN Issues (Missing Libraries)

**Symptoms**

* Errors in logs like:
  `Unable to load any of {libcudnn_ops.so...}`
  `Invalid handle. Cannot load symbol cudnnCreateTensorDescriptor`
* Container/service crashes

**Cause**

* Wrong or incomplete CUDA image (without cuDNN)
* Incorrect cuDNN version for the model

**Solution**

* Use a matching CUDA+cuDNN image (see above)
* In the container, check:

  ```sh
  ls /usr/lib/x86_64-linux-gnu/libcudnn*
  ```
* If missing, switch base image or install cuDNN explicitly ([Nvidia CUDA / cuDNN Images on Docker Hub](https://hub.docker.com/r/nvidia/cuda/tags?name=12.6))

---

## 3. Audio/ALSA Errors in Container

**Symptoms**

* Many `ALSA lib ...` or `Unknown PCM ...` errors in logs
* JACK server errors

**Meaning & Solution**

* **Harmless if no audio output is needed inside the container!**
* Occurs because no sound card exists in the container.
* Audio processing (e.g., Whisper, VAD) still works (file-based).
* Can be safely ignored.

---

## 4. “Failed to upload audio” / WebSocket Errors

**Symptoms**

* Audio upload fails, app crashes or restarts

**Causes & Solutions**

* **cuDNN not found** (see above): Adjust the image.
* **Browser/CORS/HTTPS:**

  * Frontend must run over HTTPS, otherwise the browser blocks audio/mic.
  * Check CORS settings in FastAPI.
* **Disk full:**

  * Check WSL/Docker disk usage and clean if necessary.
* **Check logs and browser console** to distinguish client vs server issues.

---

## 5. Python and pip Missing in Base Image

**Symptoms**

* Docker build fails with "`pip: not found`"

**Cause**

* CUDA base images usually don’t include Python

**Solution**

* Install Python/pip in Dockerfile:

  ```dockerfile
  RUN apt-get update && apt-get install -y python3 python3-pip
  ```

---

## 6. Disk Space in Docker-WSL (Windows)

**To check**

* C:\ drive is full because Docker & WSL store data on the system partition.
* VHDX files not shrinking.

**Solution**

1. **Clean up containers, images, and build cache:**

   * **Warning:** Never run `docker system prune -a` without double-checking — it deletes all unused Docker data.
   * Safer approach:

     ```sh
     docker system df
     docker builder prune
     ```

2. **Shut down Docker & WSL completely:**

   * Close Docker and verify no Docker processes in Task Manager.
   * Then run the following in Powershell (if on Windows) as admin:

     ```sh
     wsl --shutdown
     ```

3. **Shrink the VHDX file (again PowerShell as Admin):**

  3.1 **Hyper-V:**
    ```powershell
    Optimize-VHD -Path "C:\Users\<USERNAME>\AppData\Local\Docker\wsl\disk\docker_data.vhdx" -Mode Full
    ```

    Replace `<USERNAME>` accordingly.

  3.2 **Without Hyper-V**
    ```powershell
    diskpart

    select vdisk file="C:\Users\<USERNAME>\AppData\Local\Docker\wsl\disk\docker_data.vhdx"
    attach vdisk readonly
    compact vdisk
    detach vdisk
    exit
    ```

    Replace `<USERNAME>` accordingly.


4. **Restart Docker Desktop**
   → Disk space should now be freed.
