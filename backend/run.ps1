$ErrorActionPreference="Stop"
if (-not (Test-Path ".venv")) { py -3.11 -m venv .venv }
& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
