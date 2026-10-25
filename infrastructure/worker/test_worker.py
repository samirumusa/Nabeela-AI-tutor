import asyncio
import base64
import unittest
import io
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch
import httpx
from fastapi import HTTPException
from fastapi.testclient import TestClient
from infrastructure.worker import gateway
from infrastructure.worker.supervise import wait_ready, stop_children, launch_service, relay_output, check_warmup_response
from infrastructure.worker.test_endpoint import extract_reply, send, safe_error


class WorkerTests(unittest.TestCase):
    def test_warmup_error_reports_redacted_detail(self):
        response = httpx.Response(500, json={"detail": "ASR failed private-test-token"},
                                  request=httpx.Request("POST", "http://localhost/warmup"))
        with patch.dict("os.environ", {"MASTER_TOKEN": "private-test-token"}), \
             patch("infrastructure.worker.supervise.progress") as output:
            with self.assertRaises(httpx.HTTPStatusError):
                check_warmup_response(response, "Voice conversation warmup")
        self.assertIn("ASR failed [REDACTED]", output.call_args.args[0])
        self.assertNotIn("private-test-token", output.call_args.args[0])

    def test_successful_warmup_does_not_log_payload(self):
        response = httpx.Response(200, json={"transcript": "private"},
                                  request=httpx.Request("POST", "http://localhost/warmup"))
        with patch("infrastructure.worker.supervise.progress") as output:
            check_warmup_response(response, "warmup")
        output.assert_not_called()

    def test_error_details_redact_credentials(self):
        message = safe_error(Exception("Failed HTTP 401 https://host?api_key=secret-value Authorization: Bearer secret-value"), "secret-value")
        self.assertIn("HTTP 401", message)
        self.assertNotIn("secret-value", message)
        self.assertNotIn("https://host", message)

    def test_cloud_client_unwraps_and_validates_wav(self):
        wav = b"RIFF" + b"\0" * 4 + b"WAVE" + b"\0" * 32
        result, audio = extract_reply({"response": {"tutor_text": "Try again", "audio_base64": base64.b64encode(wav).decode()}})
        self.assertEqual(audio, wav)
        self.assertEqual(result["tutor_text"], "Try again")
        with self.assertRaises(ValueError):
            extract_reply({"response": {"detail": "unavailable"}})

    def test_cloud_client_disables_automatic_retries(self):
        endpoint = AsyncMock()
        asyncio.run(send(endpoint, b"wav", 10))
        self.assertEqual(endpoint.request.call_args.args[0], "/voice")
        self.assertFalse(endpoint.request.call_args.kwargs["retry"])
        self.assertEqual(endpoint.request.call_args.kwargs["cost"], 1)

    def test_child_stdout_stderr_stream_to_console_and_file(self):
        children, relays = [], []
        console = io.StringIO()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "service.log"
            log = path.open("a", encoding="utf-8")
            with patch("infrastructure.worker.supervise.open", return_value=log), \
                 patch("infrastructure.worker.supervise.sys.stdout", console), \
                 patch.dict("os.environ", {"MASTER_TOKEN": "private-test-token"}):
                child = launch_service("test", [sys.executable, "-u", "-c",
                    "import sys; print('model loading'); print('private-test-token', file=sys.stderr)"], children, relays)
                self.assertEqual(child.wait(timeout=10), 0)
                relays[0].join(timeout=5)
            self.assertFalse(relays[0].is_alive())
            self.assertIn("[test] model loading", console.getvalue())
            self.assertIn("[REDACTED]", console.getvalue())
            self.assertNotIn("private-test-token", console.getvalue())
            self.assertIn("model loading", path.read_text())
            self.assertNotIn("private-test-token", path.read_text())
            self.assertTrue(log.closed)

    def test_closed_console_does_not_prevent_log_drain(self):
        from unittest.mock import Mock
        class RetainedLog(io.StringIO):
            def close(self):
                self.saved = self.getvalue()
                super().close()
        console = Mock()
        console.write.side_effect = BrokenPipeError()
        log = RetainedLog()
        relay_output("test", io.BytesIO(b"first\nsecond\n"), log, console, ())
        self.assertEqual(log.saved, "first\nsecond\n")

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
