# Docker Scaddy Remote Control - Setup Guide (English)

This project allows you to remotely start and stop a Docker stack (e.g., Scaddy) on a remote GPU "server" from a Windows laptop. This guide explains how to set up the necessary scripts and tools for automatic control of the Docker stack during system startup as well as when closing the browser to correctly stop the Docker stack after usage, so GPU and other resources are freed up again.

## 📋 Prerequisites

- Windows Laptop (Client, we used Win10)
- Remote GPU PC (Server, user: livinglab) with Docker Compose installed
- Stable network connection (WiFi or LAN)
- Putty and Plink installed (both must be in the system path)

---

## 📁 Directory Structure

```
C:\Users\user\Desktop\Start_Scaddy_remotely
├── startScaddy.bat (Start/Autostart script)
├── plink.exe (or in system path)
├── start_via_bat_readme.md
```

---

## Usage 

- double click on the ´startScaddy.bat´ on the desktop - this will do all magic
- be sure to be connected to the UL-network
- attention: closing the browser after scaddy is started stops the docker compose stack and accordingly the app.

---

## 🛠️ Installation and Setup

### 1. Create the Directory

Create the directory C:\\Users\\PC\\Desktop\\Start_Scaddy_remotely and create all necessary files.

### 2. Install Putty and Plink

- Download Putty and Plink from the official website.
- Make sure both are in the system path (PATH)

### 3. Accept the SSH Host Key

Open Putty and connect to the remote GPU server once to ensure the SSH host key is added to the registry:

1. Open Putty.
2. Enter the IP address of your remote GPU server.
3. Click Open.
4. Accept the SSH host key when prompted.
5. Log in with your username and password.
6. Close the Putty session.

This step is required to avoid the host key confirmation during automated SSH connections.

### 4. Create the Start Script (startmagicmirror.bat)

Create the file startScaddy.bat with the following content:

```bat
@echo off
REM === Configuration ===
set SSH_USER=[user]
set SSH_HOST=[ip]
set SSH_PASSWORD=[password]
set DOCKER_PROJECT=scaddy-team
set DOCKER_PATH=[...]
set BROWSER_URL=https://[ip]:8112
REM for credentials and stuff ask Team Living Lab. We're happy to help :)

REM === Check, if plink.exe is ready ===
where plink.exe >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Fehler: plink.exe wurde nicht gefunden. Bitte plink installieren und in den PATH legen. / plink.exe not found, check if installed or write it to PATH
    pause
    exit /b
)

REM Check if the Docker stack is already running
echo Checking if the Docker stack is already running...
set STACK_STATUS=
for /f "tokens=*" %%i in ('plink -batch -pw %SSH_PASSWORD% %SSH_USER%@%SSH_HOST% "docker ps -q -f label=com.docker.compose.project=%DOCKER_PROJECT%"') do set STACK_STATUS=%%i

if "%STACK_STATUS%" == "" (
    echo Docker stack is not running, starting now...
    echo y | plink -batch -pw %SSH_PASSWORD% %SSH_USER%@%SSH_HOST% "cd %DOCKER_PATH% && docker compose -p %DOCKER_PROJECT% up -d"
    echo Docker stack started.
) else (
    echo Docker stack is already running. Not starting again.
)

REM wait for stack to start
timeout /t 12

REM start firefox, check path if neccessary!
set FIREFOX_PATH="C:\Program Files\Mozilla Firefox\firefox.exe"
if not exist %FIREFOX_PATH% (
    set FIREFOX_PATH="C:\Program Files (x86)\Mozilla Firefox\firefox.exe"
)
if not exist %FIREFOX_PATH% (
    echo Fehler: Firefox wurde nicht gefunden! Bitte installiere Firefox oder passe den Pfad an. / Firefox not found
    pause
    exit /b
)

start "" %FIREFOX_PATH% %BROWSER_URL%

REM wait for the browser to open
timeout /t 2

REM watch browser process 
:WATCH_BROWSER
tasklist /FI "IMAGENAME eq firefox.exe" | find /I "firefox.exe" >nul
if %errorlevel% == 0 (
    REM browser still running - check again in 5s
    timeout /t 5
    goto WATCH_BROWSER
)

REM if browser is closed, stop the docker stack!
echo Browser geschlossen. Stopping Docker stack...
plink -batch -pw %SSH_PASSWORD% %SSH_USER%@%SSH_HOST% "docker compose -p %DOCKER_PROJECT% stop"

echo Vorgang abgeschlossen. Du kannst dieses Fenster nun schließen. / Scaddy is stopped, you can close the cmd-window now.
pause
exit
```

### 5. Add to Autostart

Copy the startScaddy.bat file to your startup folder:

```
C:\Users\YOUR_USERNAME\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\ (could look different under other language settings)
```

### 6. Testing

- Make sure your network connection is stable.
- Restart your laptop and check if the Docker stack is correctly started from startup and stopped when you close the browser.
- Important: Always close the browser first (which stops the Stack and frees resources) and then shutdown.

---

## 📝 Important Notes

- Make sure plink.exe is in the system path.
- The SSH host key must be manually accepted via Putty as described in step 3.
- If the Stack won't start there could be possibly a problem with docker or sth.: in that case contact Team Living Lab (Thomas / Oliver).

---

## 🚀 Good Luck!

With this setup, your Docker stack should start and stop correctly. 😊