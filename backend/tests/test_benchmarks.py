import asyncio
import json
from pathlib import Path
import tempfile
import unittest

from benchmarks.evaluate import evaluate, load_manifest, normalize, score


class EvaluationTests(unittest.TestCase):
    def test_normalization_preserves_hausa_letters_and_grammar(self):
        self.assertEqual(normalize("Ƙofa, I GO market!"), "ƙofa i go market")

    def test_correction_is_not_preservation(self):
        checks = [{"spoken": "I go market", "corrections": ["I went to the market"]}]
        exact = score("Yesterday I go market", "Yesterday I go market.", checks)
        corrected = score("Yesterday I go market", "Yesterday I went to the market", checks)
        self.assertEqual(exact["wer"], 0)
        self.assertTrue(exact["preservation_checks"][0]["preserved"])
        self.assertEqual(corrected["wer"], 0.75)
        self.assertFalse(corrected["preservation_checks"][0]["preserved"])
        self.assertTrue(corrected["preservation_checks"][0]["correction_detected"])

    def test_empty_hypothesis_is_all_deletions(self):
        self.assertEqual(score("Ina son", "", [])["wer"], 1)

    def test_manifest_requires_all_categories(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "manifest.json"
            path.write_text(json.dumps({"version": 1, "cases": []}))
            with self.assertRaises(ValueError):
                load_manifest(path)

    def test_missing_recordings_never_count_as_evaluated(self):
        manifest = load_manifest(Path("benchmarks/manifest.v1.json"))
        class NoCalls:
            async def transcribe(self, *args):
                raise AssertionError("Must not transcribe unconsented audio")
        # User recordings and consent flags change during real benchmarking.
        # Use an empty directory rather than depending on their absence locally.
        with tempfile.TemporaryDirectory() as folder:
            report = asyncio.run(evaluate(manifest, Path(folder), NoCalls()))
        self.assertFalse(report["complete"])
        self.assertTrue(all(row["status"] == "unavailable" for row in report["results"]))

    def test_runner_uses_provider_and_records_raw_text(self):
        class FakeASR:
            async def transcribe(self, audio, filename, language):
                return {"text": "Yesterday I go market", "detected_language": "en"}
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            (base / "test.wav").write_bytes(b"test audio")
            manifest = {"version": 1, "cases": [{"id": "test", "category": "learner_errors",
                        "audio": "test.wav", "consented": True, "reference": "Yesterday I go market"}]}
            report = asyncio.run(evaluate(manifest, base, FakeASR()))
            self.assertTrue(report["complete"])
            self.assertEqual(report["results"][0]["transcription"]["text"], "Yesterday I go market")


if __name__ == "__main__":
    unittest.main()
