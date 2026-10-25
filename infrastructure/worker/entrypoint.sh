#!/bin/bash
set -euo pipefail
/opt/voice/bin/python -u -m infrastructure.worker.speech_preflight
export LD_LIBRARY_PATH="$(/opt/voice/bin/python -c 'import nvidia.cublas.lib, nvidia.cudnn.lib; print(nvidia.cublas.lib.__path__[0] + ":" + nvidia.cudnn.lib.__path__[0])'):${LD_LIBRARY_PATH:-}"
exec python3 -m infrastructure.worker.supervise
