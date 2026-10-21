"""Vast PyWorker entrypoint, started after readiness by supervise.py."""
import base64
from pathlib import Path


def benchmark_payload():
    # Supervisor generates this English clip with Kokoro. Capacity estimation
    # exercises the full pipeline; synthetic speech is not ASR quality evidence.
    return {"audio_base64": base64.b64encode(Path("/tmp/nabeela-benchmark.wav").read_bytes()).decode("ascii")}


def main():
    from vastai import Worker, WorkerConfig, HandlerConfig, BenchmarkConfig, LogActionConfig
    Worker(WorkerConfig(
        model_server_url="http://127.0.0.1", model_server_port=18000,
        model_log_file="/tmp/nabeela-ready.log",
        model_healthcheck_url="http://127.0.0.1:18000/ready",
        handlers=[HandlerConfig(route="/voice", allow_parallel_requests=False,
            workload_calculator=lambda payload: 1.0,
            max_queue_time=5.0,
            benchmark_config=BenchmarkConfig(generator=benchmark_payload, runs=2, concurrency=1))],
        log_action_config=LogActionConfig(on_load=["NABEELA_READY"]),
        max_sessions=1,
    )).run()


if __name__ == "__main__":
    main()
