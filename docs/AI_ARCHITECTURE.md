# AI Architecture

## Target pipeline
`Microphone -> VAD/cleanup -> ASR -> language/router -> tutor -> evidence extraction -> mastery engine -> response -> language-aware TTS -> audio`

## Current prototype
`Audio -> faster-whisper -> MockTutorProvider -> Kokoro -> audio`

## Components
### ASR
Must support Hausa, Hausa-accented English and code-switching, while preserving learner errors. Current baseline is faster-whisper. Future providers may include Nigerian-language/accent models.

### Tutor
The tutor manages conversation, explanations, adaptive prompts and structured evidence. `MockTutorProvider` is intentional during integration. N-ATLaS or another model can later implement the same provider contract.

### Evidence extractor
Produces structured evidence rather than a single opaque score: grammar, vocabulary, comprehension, fluency, speaking objectives, target-item usage, support required and confidence.

### Mastery engine
Backend authority for progression. The LLM supplies evidence but does not promote learners directly.

### Pronunciation
Separate concern from ASR. Future implementation should use phoneme/forced-alignment or pronunciation-scoring logic validated with humans; ASR confidence alone is not a pronunciation score.

### TTS
Kokoro is the English baseline. Hausa requires a dedicated Hausa-capable voice. Mixed responses require language segmentation and synthesis routing, then audio concatenation/streaming.

## Provider interfaces
Keep replaceable interfaces for ASR, tutor, TTS, pronunciation and persistence. Business/domain logic should depend on interfaces, not model SDKs.

## Cost principle
Prefer self-hosted/open components, deterministic rules and cached/static lesson audio. Route simple operations away from large models. No paid API should be assumed.
