"""Run from backend: python -m benchmarks.evaluate manifest.json --output report.json."""
import argparse
import asyncio
from collections import Counter
from datetime import datetime, timezone
import json
from importlib.metadata import version
from pathlib import Path
import time
import unicodedata

CATEGORIES = {"hausa", "hausa_accented_english", "code_switching", "learner_errors"}


def normalize(text):
    # Keep Hausa letters and actual grammar; ignore casing and punctuation only.
    text = unicodedata.normalize("NFC", text).casefold()
    return " ".join("".join(c if c.isalnum() or c.isspace() else " " for c in text).split())


def distance(reference, hypothesis):
    row = list(range(len(hypothesis) + 1))
    for i, left in enumerate(reference, 1):
        next_row = [i]
        for j, right in enumerate(hypothesis, 1):
            next_row.append(min(next_row[-1] + 1, row[j] + 1, row[j - 1] + (left != right)))
        row = next_row
    return row[-1]


def contains(text, phrase):
    return f" {normalize(phrase)} " in f" {normalize(text)} "


def score(reference, hypothesis, checks):
    ref, hyp = normalize(reference), normalize(hypothesis)
    words, chars = ref.split(), list(ref.replace(" ", ""))
    word_errors = distance(words, hyp.split())
    char_errors = distance(chars, list(hyp.replace(" ", "")))
    return {
        "word_errors": word_errors, "reference_words": len(words),
        "character_errors": char_errors, "reference_characters": len(chars),
        "wer": word_errors / len(words), "cer": char_errors / len(chars),
        "preservation_checks": [
            {"spoken": check["spoken"], "preserved": contains(hypothesis, check["spoken"]),
             "correction_detected": any(contains(hypothesis, value) for value in check["corrections"])}
            for check in checks
        ],
    }


def load_manifest(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != 1 or not data.get("cases"):
        raise ValueError("Expected a version 1 manifest with cases")
    ids = set()
    for case in data["cases"]:
        if case["id"] in ids or case["category"] not in CATEGORIES:
            raise ValueError("Duplicate ID or unknown category")
        ids.add(case["id"])
        if case.get("language", "auto") not in {"auto", "ha", "en"}:
            raise ValueError("Invalid language hint")
        if not normalize(case["reference"]):
            raise ValueError("Reference cannot be empty")
        checks = case.get("error_checks", [])
        if case["category"] == "learner_errors" and not checks:
            raise ValueError("Learner-error cases require error_checks")
        for check in checks:
            if not normalize(check["spoken"]) or not contains(case["reference"], check["spoken"]) or not check["corrections"]:
                raise ValueError("Error checks require a spoken reference phrase and corrections")
    if {case["category"] for case in data["cases"]} != CATEGORIES:
        raise ValueError("All four benchmark categories are required")
    return data


async def evaluate(manifest, base, provider):
    results = []
    for case in manifest["cases"]:
        result = {"id": case["id"], "category": case["category"], "reference": case["reference"],
                  "requested_language": case.get("language", "auto")}
        path = base / case["audio"]
        if case.get("consented") is not True or not path.is_file():
            result.update(status="unavailable", reason="Consented recording required")
        else:
            start = time.perf_counter()
            try:
                transcript = await provider.transcribe(path.read_bytes(), path.name, result["requested_language"])
                result.update(status="evaluated", transcription=transcript,
                              metrics=score(case["reference"], transcript["text"], case.get("error_checks", [])))
            except Exception as exc:
                result.update(status="error", reason=str(exc))
            result["elapsed_seconds"] = time.perf_counter() - start
        results.append(result)
    summary = {}
    for category in sorted(CATEGORIES):
        rows = [r for r in results if r["category"] == category and r["status"] == "evaluated"]
        counts = Counter()
        checks = []
        for row in rows:
            metrics = row["metrics"]
            counts.update({key: metrics[key] for key in ("word_errors", "reference_words", "character_errors", "reference_characters")})
            checks.extend(metrics["preservation_checks"])
        summary[category] = {
            "evaluated": len(rows),
            "wer": counts["word_errors"] / counts["reference_words"] if rows else None,
            "cer": counts["character_errors"] / counts["reference_characters"] if rows else None,
            "error_checks": len(checks),
            "errors_preserved": sum(c["preserved"] and not c["correction_detected"] for c in checks),
        }
    return {"manifest_version": manifest["version"], "created_at": datetime.now(timezone.utc).isoformat(),
            "complete": all(r["status"] == "evaluated" for r in results), "summary": summary, "results": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = load_manifest(args.manifest)
    from app.config import settings
    from app.providers.asr import FasterWhisperASRProvider
    report = asyncio.run(evaluate(manifest, args.manifest.parent, FasterWhisperASRProvider()))
    report["model"] = {key: getattr(settings, "whisper_" + key) for key in ("model", "device", "compute_type", "cpu_threads")}
    report["runtime_versions"] = {name: version(name) for name in ("faster-whisper", "ctranslate2")}
    report["decoding"] = {"task": "transcribe", "beam_size": 5, "temperature": 0.0,
                          "vad_filter": True, "condition_on_previous_text": True}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    raise SystemExit(0 if report["complete"] else 2)


if __name__ == "__main__":
    main()
