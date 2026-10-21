from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    kokoro_base_url: str = "http://127.0.0.1:7860"
    kokoro_voice: str = "af_heart"
    kokoro_model: str = "kokoro"
    request_timeout_seconds: float = 120.0

    # Local multilingual ASR. "small" is the first quality/speed compromise to test
    # for Hausa, Hausa-accented English and Hausa/English code switching.
    whisper_model: str = "small"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    whisper_cpu_threads: int = 8

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
