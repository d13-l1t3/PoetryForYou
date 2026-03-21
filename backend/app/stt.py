from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional


@lru_cache(maxsize=1)
def _load_model(model_name: str):
    try:
        from faster_whisper import WhisperModel
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "Speech-to-text is not installed. Install backend/requirements-audio.txt"
        ) from e

    # Force CPU to avoid CUDA / cublas DLL issues on Windows.
    # Your CPU is strong enough, а модели small хватает для проекта.
    return WhisperModel(model_name, device="cpu", compute_type="int8")


def transcribe_audio(file_path: str, model_name: str = "small") -> str:
    model = _load_model(model_name)
    segments, _info = model.transcribe(file_path, beam_size=5)
    return " ".join(seg.text.strip() for seg in segments).strip()

