from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

import httpx

from .settings import Settings


def final_video_candidates(task: dict[str, Any]) -> list[str]:
    """Return rendered MPT outputs, preferring the final video with voice/subtitles."""
    return list(task.get("videos") or task.get("combined_videos") or [])


def normalize_transition(value: Any) -> Any:
    """Translate our human-friendly config into the MPT API enum value."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"none", "off", "false"}:
        return None
    return text


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

    def _mpt_root(self) -> Path:
        return (self.settings.root / "MoneyPrinterTurbo").resolve()

    def _local_videos_dir(self) -> Path:
        value = os.getenv("MPT_LOCAL_VIDEOS_DIR", "").strip()
        if value:
            return Path(value).resolve()
        return self._mpt_root() / "storage" / "local_videos"

    def _ensure_windows_cyrillic_font(self) -> str:
        """Use a Windows UI font with native Cyrillic glyphs without committing it.

        MPT's default STHeiti is intended for CJK text and produced visibly poor
        Russian subtitle spacing in our first pilot render. On Windows we copy an
        already-installed system font into MPT's ignored local runtime tree. The
        font file is never committed or distributed by VV_knopka.
        """
        video_cfg = self.settings.raw.get("video", {})
        configured = str(video_cfg.get("subtitle_font_name") or "VVKnopka-Cyrillic.ttf")
        fonts_dir = self._mpt_root() / "resource" / "fonts"
        fonts_dir.mkdir(parents=True, exist_ok=True)
        destination = fonts_dir / configured
        if destination.exists() and destination.stat().st_size > 0:
            return configured

        if os.name == "nt":
            windows_dir = Path(os.environ.get("WINDIR", r"C:\Windows"))
            candidates = [
                windows_dir / "Fonts" / "arialbd.ttf",
                windows_dir / "Fonts" / "segoeuib.ttf",
                windows_dir / "Fonts" / "arial.ttf",
                windows_dir / "Fonts" / "segoeui.ttf",
            ]
            for source in candidates:
                if source.exists():
                    shutil.copy2(source, destination)
                    return configured

        # Non-Windows/test fallback: leave MPT on one of its bundled fonts.
        return "MicrosoftYaHeiBold.ttc"

    def _ffmpeg_binary(self) -> str:
        return os.getenv("IMAGEIO_FFMPEG_EXE", "").strip() or shutil.which("ffmpeg") or "ffmpeg"

    def _prepare_vertical_materials(self, materials: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Replace landscape local footage with 9:16 blur-fill derivatives.

        MPT preserves mismatched aspect ratios by putting the source over a black
        canvas. For Shorts that creates large black bars. We pre-render only the
        landscape sources into portrait files: a blurred full-frame background
        fills 9:16 while the complete original frame remains sharp in the center.
        Portrait stock is left untouched.
        """
        local_dir = self._local_videos_dir()
        local_dir.mkdir(parents=True, exist_ok=True)
        prepared: list[dict[str, Any]] = []

        for material in materials:
            item = dict(material)
            source_info = dict(item.get("source_info") or {})
            width = int(source_info.get("width") or 0)
            height = int(source_info.get("height") or 0)
            filename = str(item.get("url") or "")

            if width <= height or not filename:
                prepared.append(item)
                continue

            source = local_dir / filename
            if not source.exists():
                prepared.append(item)
                continue

            output = source.with_name(f"{source.stem}-vv916.mp4")
            if not output.exists() or output.stat().st_size == 0:
                filter_complex = (
                    "[0:v]split=2[bg][fg];"
                    "[bg]scale=1080:1920:force_original_aspect_ratio=increase,"
                    "crop=1080:1920,gblur=sigma=32[bgv];"
                    "[fg]scale=1080:1920:force_original_aspect_ratio=decrease[fgv];"
                    "[bgv][fgv]overlay=(W-w)/2:(H-h)/2,format=yuv420p[v]"
                )
                command = [
                    self._ffmpeg_binary(),
                    "-y",
                    "-i",
                    str(source),
                    "-filter_complex",
                    filter_complex,
                    "-map",
                    "[v]",
                    "-an",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-crf",
                    "21",
                    "-movflags",
                    "+faststart",
                    str(output),
                ]
                completed = subprocess.run(command, capture_output=True, text=True, check=False)
                if completed.returncode != 0 or not output.exists() or output.stat().st_size == 0:
                    detail = (completed.stderr or completed.stdout or "").strip()[-2000:]
                    raise RuntimeError(f"Failed to prepare 9:16 stock material {source.name}: {detail}")

            item["url"] = output.name
            source_info["vertical_fit"] = "blur_fill"
            source_info["original_local_file"] = filename
            source_info["prepared_width"] = 1080
            source_info["prepared_height"] = 1920
            item["source_info"] = source_info
            prepared.append(item)

        return prepared

    def create_ai_video(
        self,
        plan: dict[str, Any],
        language: str,
        *,
        materials: list[dict[str, Any]] | None = None,
    ) -> str:
        video_cfg = self.settings.raw["video"]
        audio_cfg = self.settings.raw["audio"]
        voice = audio_cfg["edge_voice_ru"] if language == "ru" else audio_cfg["edge_voice_en"]
        use_curated_materials = bool(materials)
        prepared_materials = self._prepare_vertical_materials(materials or []) if use_curated_materials else None
        font_name = self._ensure_windows_cyrillic_font() if language == "ru" else str(
            video_cfg.get("subtitle_font_name_en") or "BeVietnamPro-Bold.ttf"
        )

        payload = {
            "video_subject": plan["title"],
            "video_script": plan["script"],
            "video_terms": plan["search_terms"],
            "video_aspect": video_cfg["aspect"],
            # Random mode prioritizes one segment per unique approved source and
            # then uses later non-overlapping pieces from long sources as fallback.
            "video_concat_mode": "random" if use_curated_materials else "sequential",
            "video_transition_mode": normalize_transition(video_cfg.get("visual_transition")),
            "video_clip_duration": int(video_cfg["clip_seconds"]),
            "video_count": 1,
            "video_source": "local" if use_curated_materials else "pexels",
            "video_materials": prepared_materials,
            "video_language": language,
            "voice_name": voice,
            "voice_volume": 1.0,
            "voice_rate": 1.0,
            "bgm_type": "random",
            "bgm_volume": float(video_cfg["bgm_volume"]),
            "subtitle_enabled": bool(video_cfg["subtitle_enabled"]),
            "subtitle_position": str(video_cfg.get("subtitle_position", "custom")),
            "custom_position": float(video_cfg.get("subtitle_custom_position", 74.0)),
            "font_name": font_name,
            "font_size": int(video_cfg.get("subtitle_font_size", 52)),
            "text_fore_color": str(video_cfg.get("subtitle_color", "#FFFFFF")),
            "text_background_color": False,
            "rounded_subtitle_background": False,
            "stroke_color": str(video_cfg.get("subtitle_stroke_color", "#000000")),
            "stroke_width": float(video_cfg.get("subtitle_stroke_width", 2.2)),
            "match_materials_to_script": not use_curated_materials,
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
        candidates = final_video_candidates(task)
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
