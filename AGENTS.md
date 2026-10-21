# Nabeela — Codex Development Instructions

Nabeela is a voice-first AI English tutor designed primarily for Hausa speakers. Preserve the working system while developing incrementally.

## Product invariant
Curriculum -> Daily Mission -> 20-minute AI conversation -> evidence -> mastery update -> personalized next mission.
Learners level up because they demonstrate communication ability, not because they accumulated XP or completed pages.

## Current working stack
- FastAPI backend (`backend/`)
- faster-whisper local ASR
- `MockTutorProvider` intentionally standing in for N-ATLaS
- Kokoro TTS as the current **English** voice, exposed separately at `http://127.0.0.1:7860`
- Backend default: `http://127.0.0.1:8000`
- No paid cloud API may be introduced without explicit approval.

## Provider boundaries are mandatory
ASR, tutor/LLM, TTS, pronunciation scoring, mastery, and persistence must remain replaceable components. Do not tightly couple business logic to Whisper, N-ATLaS, Kokoro, or a future Hausa TTS.

## Hausa requirements
1. Understand natural Hausa.
2. Understand Hausa-accented English.
3. Preserve Hausa/English code-switching.
4. Preserve learner grammar errors in transcripts where possible; never silently normalize an error that is teaching evidence.
5. English<->Hausa teaching explanations must be contextual, not naive word-for-word translation.
6. Hausa audio must eventually use a dedicated natural Hausa voice. Kokoro is NOT the final Hausa TTS.
7. Mixed-language output must eventually be segmented/routed, e.g. `[HA] ... [EN] go [HA] ... [EN] went`.
8. Hausa support is a learning bridge, not a penalty. After a Hausa explanation, test the concept again in English before recording mastery.

## Teaching policy
Use English first. Small mistake -> simple English correction. Repeated confusion/difficult concept/user request -> brief Hausa bridge -> return to English application. During assessment, capture evidence before giving help.

## Mastery policy
The LLM may collect and explain evidence but MUST NOT be the sole authority for CEFR promotion. Promotion belongs to a deterministic/backend mastery engine using repeated evidence across days, required learning items, conversations, lessons, and final challenges.

## Learning-item hierarchy
Words -> Collocations -> Chunks -> Sentence Patterns -> Conversation -> Spaced Recall -> Mastery.
Track recognition separately from productive ability. Suggested lifecycle: New -> Learning -> Familiar -> Recall -> Mastered -> Review Due.

## Gamification policy
Activities may create XP, coins, badges and streaks. Evidence creates mastery. XP must never substitute for mastery. Reward meaningful speaking/learning rather than login/tapping.

## Development rules
- Inspect existing code before changing architecture.
- Preserve existing endpoints unless intentionally versioning/deprecating them.
- Add tests for new behavior.
- Prefer small reversible commits.
- Never commit secrets or `.env` files.
- Do not bundle heavyweight models into Git.
- Keep CPU/RAM constraints in mind for local Windows development.
- Document migrations and new environment variables.

## Current milestone
Validate ASR with three benchmark classes: Hausa, Hausa-accented English, and Hausa-English code-switching. Then complete microphone/audio -> ASR -> MockTutorProvider -> English TTS. Next milestones are session state/persistence, curriculum/mastery, mobile client, then dedicated Hausa TTS routing.

Read `docs/PRODUCT_SPEC.md`, `docs/AI_ARCHITECTURE.md`, and `docs/HAUSA_LANGUAGE_SPEC.md` before major changes.
