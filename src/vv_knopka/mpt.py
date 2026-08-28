from __future__ import annotations

import os
import time
from typing import Any

import httpx

from .settings import Settings


class MoneyPrinterTurboClient:
    """Thin adapter over MoneyPrinterTurbo's current /api/v1 video API."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = settings.mpt_base_url
        self.api_key = os.getenv("MPT_API_KEY", "").strip()

    def _headers(self) -> dict[str, str]:
        headers = {"x-task-id": "vv-knopka"}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        return headers

    def create_ai_video(self, plan: dict[str, Any], language: str) -> str:
        video_cfg = self.settings.raw["video"]
        audio_cfg = self.settings.raw["audio"]
        voice = audio_cfg["edge_voice_ru"] if language == "ru" else audio_cfg["edge_voice_en"]
        payload = {
            "video_subject": plan["title"],
            "video_script": plan["script"],
            "video_terms": plan["search_terms"],
            "video_aspect": video_cfg["aspect"],
            "video_concat_mode": "sequential",
            "video_transition_mode": video_cfg.get("visual_transition"),
            "video_clip_duration": int(video_cfg["clip_seconds"]),
            "video_count": 1,
            "video_source": "pexels",
            "video_language": language,
            "voice_name": voice,
            "voice_volume": 1.0,
            "voice_rate": 1.0,
            "bgm_type": "random",
            "bgm_volume": float(video_cfg["bgm_volume"]),
            "subtitle_enabled": bool(video_cfg["subtitle_enabled"]),
            "match_materials_to_script": True,
        }
        with httpx.Client(timeout=60) as client:
            response = client.post(f"{self.base_url}/api/v1/videos", headers=self._headers(), json=payload)
            response.raise_for_status()
            body = response.json()
        return body["data"]["task_id"]

    def task(self, task_id: str) -> dict[str, Any]:
        with httpx.Client(timeout=30) as client:
            response = client.get(f"{self.base_url}/api/v1/tasks/{task_id}", headers=self._headers())
            response.raise_for_status()
            return response.json()["data"]

    def wait(self, task_id: str, timeout_seconds: int = 1800, poll_seconds: float = 3.0) -> dict[str, Any]:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            task = self.task(task_id)
            state = int(task.get("state", 4))
            if state == 1:
                return task
            if state == -1:
                raise RuntimeError(f"MoneyPrinterTurbo task failed: {task.get('error') or task}")
            time.sleep(poll_seconds)
        raise TimeoutError(f"MoneyPrinterTurbo task {task_id} timed out")

    def download_video(self, task: dict[str, Any], output: str | os.PathLike[str]) -> str:
        candidates = task.get("combined_videos") or task.get("videos") or []
        if not candidates:
            raise RuntimeError("MoneyPrinterTurbo completed without a downloadable video")
        source = candidates[0]
        url = source if str(source).startswith(("http://", "https://")) else f"{self.base_url}/{str(source).lstrip('/')}"
        output_path = os.fspath(output)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with httpx.Client(timeout=300, follow_redirects=True) as client:
            response = client.get(url, headers=self._headers())
            response.raise_for_status()
            with open(output_path, "wb") as fh:
                fh.write(response.content)
        return output_path
