# Katana AI: Voice I/O Integration (`feature/voice-io`)

This document outlines the architecture for enabling voice interaction with Katana AI, as specified in the Kusanagi-v1.0 directive. It involves three main components:
1.  A local Speech-to-Text (STT) service.
2.  A local Text-to-Speech (TTS) service.
3.  A desktop client for capturing and playing back audio.

The core principle is that the main `katana-ai` application remains agnostic of the audio source. It exposes a web API that the desktop client communicates with.

## 1. System Architecture Diagram

```
[Desktop Client] <--- (Audio Stream) ---> [Katana API Server]
      |                                           |
      | 1. Records audio                          | 2. Sends audio to Whisper
      | 6. Receives audio response & plays it     | 3. Gets text back
      |                                           | 4. Sends text to Orchestrator
      |                                           | 5. Gets text response back
      |                                           | 6. Sends text to Piper
      v                                           v
[Microphone/Speaker]                       [Whisper STT] / [Piper TTS]
```

## 2. Voice Service Setup

For performance and privacy, voice processing is handled by locally hosted services, not cloud APIs.

### Speech-to-Text (STT): Whisper.cpp
- **Technology:** [Whisper.cpp](https://github.com/ggerganov/whisper.cpp) provides a high-performance C++ port of OpenAI's Whisper model.
- **Setup:**
    1. Clone the repository and follow its instructions to build the `server` executable.
    2. Download a quantized Whisper model (e.g., `ggml-base.en.bin`).
    3. Run the server: `./server -m models/ggml-base.en.bin --host 0.0.0.0`
- **API Interaction:** The server will expose an endpoint (e.g., `/inference`) that accepts a POST request with raw audio data and returns a JSON object with the transcribed text. The `api_server.py` blueprint is designed to communicate with this endpoint.

### Text-to-Speech (TTS): Piper
- **Technology:** [Piper](https://github.com/rhasspy/piper) is a fast, local neural text-to-speech system.
- **Setup:**
    1. Download the Piper software and a voice model file (e.g., `en_US-lessac-medium.onnx`).
    2. Run Piper as an HTTP server. The exact command may vary, but the goal is to expose a web endpoint.
- **API Interaction:** The server will expose an endpoint (e.g., `/tts`) that accepts a GET or POST request with text and returns a `.wav` audio stream. The `api_server.py` blueprint is designed to communicate with this endpoint.

## 3. Desktop Client

The desktop client is the user-facing component that ties the system together.

- **Technology:** A cross-platform framework like [Tauri](https://tauri.app/) or [Electron](https://www.electronjs.org/) is recommended. Tauri is preferred for its lower resource usage.
- **Responsibilities:**
    1.  **Global Hotkey:** Register a system-wide hotkey (e.g., `Cmd+Shift+Space`) to start a voice interaction.
    2.  **Audio Recording:** On hotkey press, start recording audio from the default microphone. Use a library like `node-vad` for voice activity detection to automatically stop recording when the user finishes speaking.
    3.  **API Communication:**
        - Send the recorded audio data (e.g., as a Blob) to the `katana-ai` `api_server.py`'s `/voice_command` endpoint via a POST request.
        - Receive the audio stream in the response.
    4.  **Audio Playback:** Play the received audio stream through the default speakers.
    5.  **State Management:** Display visual feedback to the user (e.g., "Listening...", "Thinking...", "Speaking...").
