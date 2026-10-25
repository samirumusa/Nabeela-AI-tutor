import sys
import unittest
from unittest.mock import Mock, patch

from infrastructure.worker import speech_preflight


class SpeechPreflightTests(unittest.TestCase):
    def test_loads_and_exercises_tokenizer(self):
        spacy = Mock()
        spacy.load.return_value.make_doc.return_value = ["Hello"]
        with patch.dict(sys.modules, {"spacy": spacy}), \
             patch.object(speech_preflight.importlib.metadata, "version", return_value="test"), \
             patch.object(speech_preflight, "check_audio_decoder") as decoder, \
             patch("builtins.print") as output:
            speech_preflight.main()
        spacy.load.assert_called_once_with("en_core_web_sm")
        spacy.load.return_value.make_doc.assert_called_once()
        self.assertIn("English tokenizer OK", output.call_args.args[0])
        decoder.assert_called_once()

    def test_real_audio_decode_without_model_download(self):
        speech_preflight.check_audio_decoder()

    def test_tokenizer_failure_stops_startup(self):
        spacy = Mock()
        spacy.load.side_effect = OverflowError("tokenizer failure")
        with patch.dict(sys.modules, {"spacy": spacy}), \
             patch.object(speech_preflight.importlib.metadata, "version", return_value="test"), \
             patch("builtins.print"):
            with self.assertRaises(OverflowError):
                speech_preflight.main()


if __name__ == "__main__":
    unittest.main()
