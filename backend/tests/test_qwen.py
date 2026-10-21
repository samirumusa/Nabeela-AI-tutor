import asyncio
import unittest
from unittest.mock import AsyncMock, patch
import httpx
from app.providers.qwen import QwenTutorProvider


class QwenTests(unittest.TestCase):
    def test_payload_and_provider(self):
        response = httpx.Response(200, json={"choices": [{"message": {"content": "Try again."}}]}, request=httpx.Request("POST", "http://local"))
        client = AsyncMock()
        client.post.return_value = response
        with patch("app.providers.qwen.httpx.AsyncClient") as constructor:
            constructor.return_value.__aenter__.return_value = client
            result = asyncio.run(QwenTutorProvider().chat("Yesterday I go market"))
        self.assertEqual(result.provider, "qwen")
        self.assertEqual(result.language, "en")
        payload = client.post.call_args.kwargs["json"]
        self.assertEqual(payload["messages"][1]["content"], "Yesterday I go market")
        self.assertFalse(payload["chat_template_kwargs"]["enable_thinking"])

    def test_unavailable_server_is_not_silently_mocked(self):
        client = AsyncMock()
        client.post.side_effect = httpx.ConnectError("offline")
        with patch("app.providers.qwen.httpx.AsyncClient") as constructor:
            constructor.return_value.__aenter__.return_value = client
            with self.assertRaises(httpx.ConnectError):
                asyncio.run(QwenTutorProvider().chat("Hello"))
