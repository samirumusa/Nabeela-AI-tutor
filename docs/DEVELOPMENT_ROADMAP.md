# Development Roadmap

## Phase 0 — Baseline (current)
- FastAPI service
- Mock tutor provider
- Kokoro English TTS
- faster-whisper ASR
- Swagger/local development

## Phase 1 — Voice MVP
- Benchmark Hausa, Hausa-accented English and code-switching
- Add test fixtures and transcription evaluation
- Stabilize `/api/voice/conversation`
- Add conversation/session IDs and structured turn responses
- Ensure learner-error preservation is observable

## Phase 2 — Persistence & domain model
- PostgreSQL
- users/learner profiles
- courses/levels/units/lessons
- learning items and lesson targets
- conversation sessions/turns/evidence
- mastery/review scheduling

## Phase 3 — Curriculum & mastery
- A1 curriculum seed
- deterministic mastery service
- daily missions
- 20-minute meaningful-participation rules
- final challenge mechanics

## Phase 4 — Mobile MVP
- React Native/Expo
- onboarding/placement
- home/daily plan/lesson player
- microphone conversation UI
- vocabulary/progress/profile
- local audio handling and API client

## Phase 5 — Hausa voice
- benchmark dedicated Hausa TTS candidates
- language/segment router
- English Kokoro + Hausa TTS
- mixed-language audio merge/streaming
- native-speaker QA

## Phase 6 — Production AI
- benchmark N-ATLaS/alternatives
- replace mock through provider contract
- structured evidence extraction
- safety/observability/rate controls
- deployment and GPU strategy

## Phase 7 — Gamification & retention
- XP/coins/badges/streaks
- Word Vault/language sets
- side quests/boss battles
- spaced repetition notifications

## Definition of done for current milestone
A local learner can submit an audio file and receive: preserved transcript, detected language, mock tutor response and English audio; benchmark results exist for all three required speech categories.
