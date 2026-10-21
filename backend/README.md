# Nabeela Backend v0.2

Local development backend for Nabeela, an English tutor for Hausa speakers.

## Current pipeline

`Microphone/audio -> faster-whisper -> Mock N-ATLaS tutor -> Kokoro -> audio`

Current components:
- **ASR:** faster-whisper `small`, CPU INT8
- **Tutor:** mock provider (replace later with remote N-ATLaS)
- **English TTS:** local Kokoro HTTP server on port 7860
- **Hausa TTS:** not implemented yet; Kokoro Hausa pronunciation is known to be unsuitable

## Windows setup

Keep the working Kokoro Docker container running, then:

```powershell
cd nabeela-backend
Set-ExecutionPolicy -Scope Process Bypass
.\run.ps1
```

The first ASR request downloads the Whisper `small` model, so it can take several minutes. Subsequent requests reuse the local model cache.

Open:
- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/docs`

## New ASR endpoint

`POST /api/asr/transcribe`

In Swagger `/docs`:
1. Expand `/api/asr/transcribe`.
2. Click **Try it out**.
3. Upload a WAV/MP3/M4A recording.
4. Set language to `auto`, `en`, or `ha`.
5. Execute.

PowerShell example:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/asr/transcribe" `
  -F "audio=@C:\path\to\speech.wav" `
  -F "language=auto"
```

Expected JSON includes `text`, `detected_language`, and `language_probability`.

## End-to-end voice endpoint

`POST /api/voice/conversation`

It transcribes the uploaded recording, sends the transcript to the mock tutor, sends the tutor response to Kokoro, and returns JSON containing:
- transcript
- detected language
- tutor text
- base64 WAV audio

This JSON form is convenient for the mobile prototype because the app receives both assessment text and audio in one request.

## Important Hausa acceptance tests

Test at least these categories before selecting ASR permanently:
1. Hausa speech
2. Hausa-accented English
3. Hausa/English code switching
4. Learner grammar errors that must remain uncorrected in the ASR transcript

Do not judge the ASR only by normal transcription accuracy. Nabeela needs learner-error preservation so the tutor can teach from the actual mistake.

See [the versioned ASR benchmark guide](benchmarks/README.md) for consented recording fixtures, local evaluation, WER/CER and learner-error preservation checks, and offline regression tests.
