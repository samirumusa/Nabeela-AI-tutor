import asyncio
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from app.providers.asr import FasterWhisperASRProvider, _load_model


class ASRTests(unittest.TestCase):
    def test_model_loading_is_lazy_and_cached(self):
        _load_model.cache_clear()
        try:
            with patch("app.providers.asr.WhisperModel") as model:
                FasterWhisperASRProvider()
                model.assert_not_called()
                self.assertIs(_load_model(), _load_model())
                model.assert_called_once()
        finally:
            _load_model.cache_clear()

    def test_language_routing_and_decoding_preserve_raw_words(self):
        for requested, expected in [("auto", None), ("en", "en"), ("ha", "ha")]:
            with self.subTest(language=requested), patch("app.providers.asr._load_model") as load:
                load.return_value.transcribe.return_value = (
                    iter([SimpleNamespace(text=" Yesterday I go market. "), SimpleNamespace(text=" Ina so. ")]),
                    SimpleNamespace(language="ha", language_probability=0.8, duration=3.0),
                )
                result = FasterWhisperASRProvider()._transcribe_sync("test.wav", requested)
                self.assertEqual(result["text"], "Yesterday I go market. Ina so.")
                self.assertEqual(result["detected_language"], "ha")
                load.return_value.transcribe.assert_called_once_with(
                    "test.wav", task="transcribe", language=expected, beam_size=5,
                    temperature=0.0, vad_filter=True, condition_on_previous_text=True)

    def test_temp_file_removed_on_success_and_failure(self):
        for failure in (False, True):
            paths = []
            def transcribe(path, language):
                paths.append(Path(path))
                self.assertEqual(Path(path).read_bytes(), b"audio")
                if failure:
                    raise RuntimeError("decode failed")
                return {"text": "I go market"}
            with patch.object(FasterWhisperASRProvider, "_transcribe_sync", side_effect=transcribe):
                if failure:
                    with self.assertRaises(RuntimeError):
                        asyncio.run(FasterWhisperASRProvider().transcribe(b"audio"))
                else:
                    asyncio.run(FasterWhisperASRProvider().transcribe(b"audio"))
            self.assertTrue(paths)
            self.assertFalse(paths[0].exists())
