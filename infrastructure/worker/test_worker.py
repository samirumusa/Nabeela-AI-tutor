import asyncio
import base64
import unittest
from unittest.mock import AsyncMock, patch
import httpx
from fastapi import HTTPException
from fastapi.testclient import TestClient
from infrastructure.worker import gateway
from infrastructure.worker.supervise import wait_ready, stop_children


class WorkerTests(unittest.TestCase):
    def test_invalid_audio_never_reaches_backend(self):
        response = TestClient(gateway.app).post("/voice", json={"audio_base64": "!invalid!"})
        self.assertEqual(response.status_code, 400)

    def test_transport_preserves_transcript_and_returns_timing(self):
        client = AsyncMock()
        client.post.return_value = httpx.Response(200, json={"transcript": "I go market"})
        with patch.object(gateway.httpx, "AsyncClient") as constructor:
            constructor.return_value.__aenter__.return_value = client
            response = TestClient(gateway.app).post("/voice", json={"audio_base64": base64.b64encode(b"wav").decode()})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["transcript"], "I go market")
        self.assertGreaterEqual(response.json()["worker_elapsed_seconds"], 0)
        self.assertEqual(client.post.call_args.kwargs["data"]["language"], "en")

    def test_busy_worker_rejects_parallel_inference(self):
        async def run():
            async with gateway.gate:
                with self.assertRaises(HTTPException) as error:
                    await gateway.voice(gateway.VoiceRequest(audio_base64="d2F2"))
                self.assertEqual(error.exception.status_code, 429)
        asyncio.run(run())

    def test_readiness_fails_if_dependency_is_down(self):
        client = AsyncMock()
        client.get.side_effect = httpx.ConnectError("offline")
        with patch.object(gateway.httpx, "AsyncClient") as constructor:
            constructor.return_value.__aenter__.return_value = client
            self.assertEqual(TestClient(gateway.app).get("/ready").status_code, 503)

    def test_child_exit_aborts_startup(self):
        from unittest.mock import Mock
        child = Mock()
        child.poll.return_value = 1
        with self.assertRaises(RuntimeError):
            wait_ready("http://localhost", [child], float("inf"))

    def test_shutdown_terminates_and_waits(self):
        from unittest.mock import Mock
        child = Mock()
        child.poll.return_value = None
        stop_children([child])
        child.terminate.assert_called_once()
        child.wait.assert_called_once()
