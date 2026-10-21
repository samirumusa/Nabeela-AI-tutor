# ASR benchmark v1

Run commands from `backend/` using the environment installed by `run.ps1`:

```powershell
python -m unittest discover -s tests -v
python -m benchmarks.evaluate benchmarks/manifest.v1.json --output benchmarks/results/local.json
```

Tests use fake model outputs and fake HTTP providers: no model downloads or running Kokoro are needed. They verify integration contracts, not recognition quality.

The checked-in manifest contains recording scripts, not measured results. Ask consenting Hausa speakers to record each script, place files in `benchmarks/audio/`, and set `consented` to true only after permission for local evaluation is recorded privately. Keep identity/consent records outside Git. Audio is ignored by Git. Do not use synthesized speech to validate Hausa accents. Have a Hausa speaker review the mixed-language script and transcribe what was actually spoken, including errors, before evaluating. Expand with multiple speakers, natural spontaneous speech, recording conditions and held-out clips; these four scripts are only a starting point.

Keep `language: auto` for the baseline, particularly code-switching. Duplicate cases with unique IDs and `ha` or `en` hints for separate controlled comparisons. A detected language is a clip-level label, not proof that both languages survived transcription.

The runner uses the existing local provider and `WHISPER_*` settings. First inference may download the configured model; no paid API is used. Reports include raw reference/hypothesis, requested and detected language, model/decoding settings, elapsed time, per-clip WER/CER, and reference-length-weighted category WER/CER. Case, punctuation and whitespace are normalized for scoring; Hausa letters and grammar remain intact. CER excludes spaces. Error rates may exceed 1 due to insertions.

Learner-error checks look for complete token sequences from `spoken` and flag listed `corrections`. Both are reported independently, so a transcript containing both does not count as preserved. Missing phrases need human review; phrase matching is an observable diagnostic rather than a complete grammar assessment. Add checks for each known error and review unlisted rewrites manually. ASR can still normalize errors internally despite having no correction prompt.

Missing/unconsented audio and decoding failures remain visible and produce exit code 2; complete execution returns 0, which is not a quality acceptance gate. Category metrics are null when no clips were evaluated. Native-speaker review is required before accepting Hausa quality; no validated quality thresholds exist yet. Preserve reports privately because they contain learner speech transcripts.

No migrations or new environment variables are required. MockTutorProvider, Kokoro and endpoint contracts are unchanged.
