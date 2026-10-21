# Nabeela

Nabeela is a voice-first AI English tutor for Hausa speakers. It combines structured CEFR-aligned learning with daily conversation practice, evidence-based mastery, strategic Hausa explanations, vocabulary/chunk mastery, and gamification.

## Repository status
This repository packages the current working FastAPI prototype plus the product/architecture specifications needed for continued development in Codex.

## Repository layout
- `backend/` — FastAPI prototype (faster-whisper + mock tutor + Kokoro integration)
- `docs/` — product, AI, Hausa, curriculum, mastery and gamification specifications
- `mobile/` — placeholder for the React Native/Expo client
- `infrastructure/` — deployment notes/placeholders
- `tests/audio/` — local benchmark audio location (do not commit personal recordings by default)
- `AGENTS.md` — instructions for Codex/agents

## Current milestone
1. Run backend and Kokoro.
2. Benchmark local ASR on Hausa, Hausa-accented English and code-switching.
3. Stabilize end-to-end voice turn.
4. Add persistence/session state.
5. Implement curriculum and mastery engine.
6. Build mobile client.
7. Add dedicated Hausa TTS and language-aware audio routing.

See `docs/DEVELOPMENT_ROADMAP.md` for the phased plan.
