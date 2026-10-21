import json
import unittest
from unittest.mock import patch

import smoke


class SmokeTests(unittest.TestCase):
    def test_tutor_request_disables_thinking_and_checks_audio(self):
        reply = json.dumps({"choices": [{"message": {"content": "Try again."}}]}).encode()
        wav = b"RIFF" + b"\x00" * 4 + b"WAVE" + b"\x00" * 32
        with patch.object(smoke, "post", side_effect=[({}, reply), ({}, wav)]) as post, patch("builtins.print"):
            smoke.main()
        request = post.call_args_list[0].args[1]
        self.assertFalse(request["chat_template_kwargs"]["enable_thinking"])
        self.assertEqual(request["max_tokens"], 150)

    def test_rejects_non_audio_response(self):
        reply = json.dumps({"choices": [{"message": {"content": "Try again."}}]}).encode()
        with patch.object(smoke, "post", side_effect=[({}, reply), ({}, b"error")]), patch("builtins.print"):
            with self.assertRaisesRegex(RuntimeError, "WAV"):
                smoke.main()

    def test_rejects_thinking_response_before_tts(self):
        reply = json.dumps({"choices": [{"message": {"content": "<think>reasoning"}}]}).encode()
        with patch.object(smoke, "post", return_value=({}, reply)) as post:
            with self.assertRaisesRegex(RuntimeError, "non-thinking"):
                smoke.main()
        self.assertEqual(post.call_count, 1)
