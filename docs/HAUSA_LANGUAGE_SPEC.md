# Hausa Language Specification

## Three independent problems
1. **Understand speech:** Hausa, Hausa-accented English and code-switching.
2. **Understand meaning:** natural, pedagogical Hausa explanations rather than literal translation.
3. **Speak:** natural Hausa pronunciation, rhythm and accent from a Hausa-capable TTS.

## Teaching policy
- Learner understands -> continue in English.
- Small mistake -> correct in simple English.
- Repeated mistake -> brief Hausa explanation.
- Confusion -> English -> short Hausa bridge -> English application.
- Difficult grammar/abstract vocabulary -> Hausa analogy/meaning is allowed.
- Explicit `Explain in Hausa` -> Hausa explanation is allowed.
- Conversation practice -> minimize Hausa unless needed.
- Assessment -> capture evidence before helping.

Core pattern: **English -> confusion -> Hausa bridge -> English application.**

## ASR benchmark requirements
Create a versioned benchmark containing consented/test recordings for:
- natural Hausa
- Hausa-accented English
- Hausa-English code-switching
- intentionally incorrect learner English

Measure transcript accuracy plus **learner-error preservation**. Example: `Yesterday I go market` must not silently become `Yesterday I went to the market` before assessment.

## TTS routing
Do not make English Kokoro pronounce Hausa in production. Future response segmentation may look like:
`[HA] Saboda kana magana ... [EN] go [HA] ya koma [EN] went`.
Synthesize each segment with its appropriate voice and merge with natural pauses.

## Quality gate
Hausa ASR, explanations and TTS require evaluation by real Hausa speakers. Build a benchmark set before production release.
