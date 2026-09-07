# Scaddy Frontend Documentation

## 1) Overview

The Scaddy frontend is a **single‑page app** (no build step) written in **Vanilla JS + Vue 3 (CDN)**. It renders a **touch‑first UI** for tablet use and talks to the FastAPI backend via **REST** and a **WebSocket**.

* **SPA entry**: `/static/index.html` served by FastAPI (`GET /` returns this file).
* **Styling**: `/static/index.css` (custom CSS; no CSS framework).
* **i18n**: `/static/translations.js` (global `transl` object with DE/EN labels).
* **Transport**:

  * WebSocket: `wss://<host>/ws` (auto‑switches `ws://` on HTTP).
  * REST endpoints used from the UI:

    * `POST /set_language?lang=de|en`
    * `POST /audio_enabled_conversation` (audio + optional image)
    * `POST /tts_single_sentence` (returns base64 MP3 snippets)
    * `POST /add_to_conversation_protocol` (logs messages)
    * `POST /stt_knowledge_annotation` (speech‑label for Add‑Knowledge)
    * `POST /reset` (clear conversation)
* **Local persistence**:

  * `localStorage['scaddy-chat-history']`: full chat transcript (user/system/scaddy + images)
  * `localStorage['scaddy-view-states']`: whether chat/camera panes were open

The app is intentionally **dependency‑light** to run reliably on a Surface tablet (Firefox preferred), and it assumes the backend may serve a **self‑signed certificate** (user must accept the browser warning once).

---

## 2) Screenshots

### Main Interface

![Main Interface](./img/00_scaddy_main_ui_en.png)

### Main Interface (annotated)

![Main Interface Annotated](./img/01_scaddy_main_ui_en_annot.png)

### Chat View

![Chat View](./img/02_scaddy_chatview_annot.png)

### Camera (Vision) View

![Camera View](./img/03_scaddy_camview_annot.png)

### Add Knowledge View

![Knowledge View](./img/04_scaddy_knowledgeview_annot.png)

---

## 3) UI Structure (index.html)

### 3.1 Top Bar Controls

Right‑aligned controls (leftmost item pushes using CSS:`.left`):

* **Chat History** (`toggleChatView()`): opens the right‑hand **chat pane**.
* **Vision Mode** (`toggleCameraView()`): opens the camera/viewfinder pane.
* **Add Knowledge** (`toggleKnowledgeView()`): opens the visRAG “teach” pane.
* **Reset** (`resetChatHistory()`): clears local chat + signals backend `POST /reset`. Button is **green** (“Start fresh”) once there’s an active conversation.
* **Language Switch** (`toggleLanguage()`): DE/EN toggle → calls `POST /set_language?lang=…`. Also flips labels and backend response language.

### 3.2 Center Stage (“Sphere” and Subtitles)

* **Sphere** (CSS:`.sphere`):

  * Default: soft pulsing (CSS `.idle`)
  * When Playing:
    * CSS `.playing`: adds a brighter look while TTS is playing.
    * JS `playNextAudio() -> animate()`: sphere animation according to amplitude of audio to increase the connection between spoken text and Scaddys visual representation
  * Icon overlays:
    * microphone (recording)
    * brain (thinking)
    * camera/brain when Vision/Add‑Knowledge panes are active and not recording/thinking
  * Clicking the sphere triggers a playful “poke”-reaction (`pokeScaddy()`).
* **Subtitles** (`.subtitles`): shows **what Scaddy is saying** (live TTS line), detailed **status** (Listening/Thinking), or **welcome message** before first interaction.

### 3.3 Primary Buttons (below sphere)

Contextual buttons based on state:

* **Talk to Scaddy** → `startRecording()`
* **Stop** (stop TTS) → `stopPlaying()`
* **Cancel** (stop recording) → `cancelRecording()`
* **Send**:

  * Audio‑only → `sendRecording()`
  * Audio + last camera still (in Vision Mode) → `sendRecording(includePicture=true)`

### 3.4 Right‑Side Split Panes

* **Chat Pane** (`.right-container.chat`):

  * Scrollable message list (`.messages`), each message has sender class (`user|system|scaddy`) + optional inline **image**.
  * Close (X), **Help (?)** triggers a spoken + textual help via TTS.
* **Camera (Vision) Pane** (`.right-container.camera`):

  * `<video>` acts as live viewfinder.
  * **Rotate camera** toggles between `facingMode: 'environment'` and `'user'` (with mirror via `.flipped`).
  * Recent capture thumbnail appears briefly as overlay bottom‑right.
* **Add Knowledge Pane** (`.right-container.knowledge`):

  * Live viewfinder → **Take picture** → shows still preview.
  * Record a short **spoken label** (or type, if you extend the UI) → STT via `POST /stt_knowledge_annotation`.
  * **Confirm** → `POST /add_clip_embedding` (adds CLIP embedding to visRAG).

---

## 4) State & Data Flow

### 4.1 WebSocket Messages

`connectWebSocket()` connects to `/ws`. Incoming messages are JSON with `type`:

* `stt_result`:

  * `text: 'vad_service_error_no_voice'` → show localized “no voice detected” as **user** message.
  * Otherwise `text` is the STT transcription → append as **user** message.
* `scaddy_answer`:

  * `text`: the LLM response including **`#pause#` markers**.
  * Frontend splits on `#pause#`, requests **per‑sentence TTS** via `POST /tts_single_sentence` and queues the returned base64 MP3 chunks for playback.
  * Also pushes the full combined answer to chat as **scaddy**.
* (Deprecated) `tts_sentence`: previously supported raw sentence + audio.

### 4.2 Audio Recording & Submission

* Microphone via `MediaRecorder` on a `getUserMedia({ audio: true })` stream.
* `startRecording()` starts the recorder, `recorderStopAndGetBlob()` gathers chunks into WAV Blob.
* `sendRecording(includePicture)` builds `FormData`:

  * `recording=recording.wav`
  * If requested, `image=snapshot.jpg` captured from `<video>` → `<canvas>` → `toBlob()`.
* Submits to `POST /audio_enabled_conversation`.
* Meanwhile, UI shows **Thinking…** and plays the animated **dot‑dot‑dot** loader until WebSocket messages come back.

### 4.3 TTS Queue & Playback

* For each sentence, `POST /tts_single_sentence` returns `{ type:'tts_sentence', text, audio(base64) }`.
* The frontend builds a **FIFO queue** (`audioQueue`) of MP3 Blobs; `playNextAudio()` pops and plays.
* **Subtitles** show the current sentence (`spokenText`).
* **Sphere** animates to audio waveform via Web Audio API’s `AnalyserNode`, scaling size and glow based on current frequency energy.

### 4.4 Vision Capture

* Vision Mode: continuous `<video>` preview; on “send with picture” the still frame is captured to JPEG and sent with the audio.
* Add Knowledge: picture is captured first; then STT label is recorded separately and sent as **base64** JSON to `/add_clip_embedding`.

### 4.5 Persistence

* **Chat history** saved on every change (`saveChatHistory`) and restored on mount (`loadChatHistory`).
* **View states** (chat/camera open) saved and restored similarly (`saveViewStates` / `loadViewStates`).

---

## 5) Features (as implemented)

* **Bilingual UI & replies** (DE/EN) with a hard toggle; backend replies match the selected language.
* **Voice I/O**: record speech; STT result shown in chat; TTS playback with animated sphere and live subtitles.
* **Vision**: capture and send images; Scaddy combines visRAG (CLIP similarity) + VLM description on the backend.
* **Teach Scaddy** (visRAG): add labeled images to CLIP embeddings from the tablet.
* **Chat transcript**: persistent across reloads; includes images you sent.
* **Context‑aware help** for each pane (spoken + text in chat).
* **Graceful camera fallback**: tries `environment` and `user`; falls back to “any available” if constrained.

---

## 6) Usage Tips (for Operators & Demo Staff)

* **Browser**: Firefox is preferred; Chromium should work. For self‑signed HTTPS, accept the warning once.
* **Mic**: Keep the tablet mic unobstructed; speak clearly. If STT returns “no voice detected”, move closer or speak louder.
* **Camera**: Good lighting; hold steady for two seconds. For Add‑Knowledge, center the subject and avoid reflections/glare.
* **Language**: Flip the DE/EN switch before you start talking; Scaddy will match the UI selection.
* **Reset**: Use “Start fresh” between groups of visitors to clear context and make the next interaction crisp.

---

## 7) Configuration Knobs (Frontend‑side)

* **Default camera**: `defaultCameraMode` is `'environment'` (rear camera). The code auto‑adjusts if unavailable.
* **Recent capture overlay**: shows for 3 seconds; controlled by `showRecentImage` setTimeout.
* **Max Add‑Knowledge record time**: 30s safety timeout (see `toggleKnowledgeRecording()`).
* **LocalStorage keys**: change the keys in `saveChatHistory` / `saveViewStates` if you want separate profiles.

---

## 8) Styling Notes (index.css quick reference)

* **Buttons**: `.button`, variants `.cancel`, `.confirm`, `.neutral`, `.light`, `.small`.
* **Sphere**:

  * `.sphere` base, `.idle` with `@keyframes idlePulse`.
  * `.playing` brightens color while TTS is active.
* **Layout**:

  * Two main columns: center stack (`.scaddy-container`) + right pane (`.right-container`).
  * Split‑view toggles with `.split-view-active` class on both.
* **Chat bubbles**: `.message.user` (light blue), `.message.scaddy` (green tint), `.message.system` (gray).

Tweak the color palette (`#0A2743` background, green glow `rgba(0,255,153,…)`) and radii to match branding.

---

## 9) Browser Permissions

* **Microphone**: required for Talk and Add‑Knowledge labels.
* **Camera**: required for Vision Mode and Add‑Knowledge.
* **Autoplay**: TTS playback usually works interactively (user gesture present). If the browser blocks, ensure the page has interacted input (click/tap) before playing audio.

---

## 10) Error Handling & Troubleshooting

* **“Unable to access the microphone/camera”**
  Check site permissions in the browser; reload the page after granting.
* **No TTS playback**
  Some browsers disallow autoplay. Tap the sphere or a button once to grant audio context, then try again.
* **WebSocket not connecting**
  Verify backend is up and that `wss://` vs `ws://` matches the page’s protocol.
* **SSL warning**
  Expected on self‑signed certs; accept once.
* **Stuck on “Thinking…”**
  Backend might be busy; check server logs. The UI shows placeholders (`.` → `..` → `...` → “Thinking”).

---

## 11) Extending the Frontend

* **Translations**: add keys in `translations.js` under `transl.<key>.<'de'|'en'>` and reference them as `transl.KEY[lang]`.
* **New panes**: follow the pattern of `.right-container.<pane>` + `togglePane()`; manage state in `data()` and `saveViewStates()`.
* **New API calls**: add fetch helpers; prefer `POST` with JSON or `FormData` for files; report errors in chat via `chatSendMessage('system', ...)`.

---

## 12) Development & Testing

* Serve via the **FastAPI app** (recommended): it mounts `/static` and provides the WebSocket + API.
* If you must open `index.html` from disk, many features (WS, permissions, REST) won’t work — always run with the backend for full functionality.
* Use the backend’s **Swagger UI** at:

  ```
  https://localhost:8112/docs   # or your configured port
  ```

  to test endpoints in isolation.

---
