"""Persistent OBS replay markers, saved clips and halftime highlight exports."""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from secretariat_core.json_store import JSONStore


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ReplayLibrary:
    """Keep replay metadata separate from the OBS-owned media files."""

    def __init__(self, base_dir: str | Path, exports_dir: str | Path | None = None) -> None:
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.exports_dir = Path(exports_dir).resolve() if exports_dir else self.base_dir / "videos"
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        self.store = JSONStore(self.base_dir / "library.json")
        self._lock = threading.RLock()
        self._export_lock = threading.Lock()
        if exports_dir is not None:
            self._migrate_exports()

    @staticmethod
    def _default() -> dict[str, list[dict[str, Any]]]:
        return {"clips": [], "highlights": []}

    def snapshot(self, match_id: str | None = None) -> dict[str, Any]:
        with self._lock:
            payload = self.store.read(self._default())
        clips = list(payload.get("clips") or [])
        highlights = list(payload.get("highlights") or [])
        if match_id is not None:
            clips = [item for item in clips if str(item.get("match_id") or "") == str(match_id)]
            highlights = [item for item in highlights if str(item.get("match_id") or "") == str(match_id)]
        return {"clips": clips, "highlights": highlights, "videos_directory": str(self.exports_dir if match_id is None else self.match_directory(match_id))}

    def create_highlights(self, *args, **kwargs):
        with self._export_lock:
            return self._create_highlights(*args, **kwargs)

    def _migrate_exports(self):
        payload = self.store.read(self._default())
        changed = False
        for item in payload.get("highlights", []):
            for key in ("path", "thumbnail"):
                old = Path(item.get(key) or "")
                if not old.is_file() or old.parent.resolve() != (self.base_dir / "videos").resolve():
                    continue
                destination = self.match_directory(item.get("match_id") or "") / old.name
                try:
                    if not destination.exists():
                        temporary = destination.with_suffix(destination.suffix + ".migrating")
                        shutil.copy2(old, temporary)
                        temporary.replace(destination)
                    if destination.stat().st_size == old.stat().st_size:
                        item[key] = str(destination)
                        changed = True
                except OSError:
                    continue  # Keep the original usable path if the disk is full.
        if changed:
            self.store.write(payload)

    def match_directory(self, match_id: str) -> Path:
        name = "".join(c for c in str(match_id) if c.isalnum() or c in "-_")[:100] or "Sin-partido"
        directory = self.exports_dir / name
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def create_marker(
        self,
        *,
        match_id: str,
        label: str,
        match_time: str = "",
        event_id: str = "",
        team: str = "",
        player: str = "",
        post_roll_seconds: float = 0,
        period: int = 1,
        event_type: str = "",
        assistant: str = "",
    ) -> dict[str, Any]:
        marker = {
            "id": uuid.uuid4().hex,
            "match_id": str(match_id or ""),
            "event_id": str(event_id or ""),
            "period": max(1, int(period)),
            "event_type": event_type or label,
            "assistant": assistant,
            "tags": [event_type or label],
            "label": str(label or "Replay").strip()[:120] or "Replay",
            "match_time": str(match_time or "").strip()[:20],
            "team": str(team or "").strip()[:80],
            "player": str(player or "").strip()[:120],
            "post_roll_seconds": max(0, min(20, float(post_roll_seconds or 0))),
            "created_at": _now(),
            "status": "pending",
            "path": "",
            "filename": "",
            "included": True,
            "error": "",
            "backend": "obs-native",
            "angles": [],
            "composition": [],
        }
        with self._lock:
            payload = self.store.read(self._default())
            payload.setdefault("clips", []).insert(0, marker)
            payload["clips"] = payload["clips"][:200]
            self.store.write(payload)
        return dict(marker)

    def update_marker(self, marker_id: str, match_id: str, **fields: Any) -> dict[str, Any]:
        allowed = {"label", "event_type", "event_id", "team", "player", "assistant"}
        with self._lock:
            data = self.store.read(self._default())
            row = next((c for c in data.get("clips", []) if c.get("id") == marker_id and c.get("match_id") == match_id), None)
            if row is None:
                raise KeyError(marker_id)
            row.update({k: str(v)[:120] for k, v in fields.items() if k in allowed})
            self.store.write(data)
            return dict(row)

    def complete_marker(self, marker_id: str, media_path: str) -> dict[str, Any]:
        resolved = Path(str(media_path or "")).expanduser().resolve()
        if not resolved.is_file():
            raise RuntimeError("OBS indicó un clip que no existe en disco")
        with self._lock:
            payload = self.store.read(self._default())
            marker = next((row for row in payload.get("clips", []) if row.get("id") == marker_id), None)
            if marker is None:
                raise KeyError(marker_id)
            marker.update({
                "status": "ready",
                "path": str(resolved),
                "filename": resolved.name,
                "saved_at": _now(),
                "error": "",
                "size_bytes": resolved.stat().st_size,
            })
            self.store.write(payload)
            return dict(marker)

    def complete_multicam_marker(self, marker_id: str, saved_paths: list[dict[str, Any] | str]) -> dict[str, Any]:
        # Archive marked angles before the plugin clears its temporary buffer.
        archive = self.base_dir / "clips" / marker_id
        archive.mkdir(parents=True, exist_ok=True)
        angles: list[dict[str, Any]] = []
        for index, value in enumerate(saved_paths):
            if isinstance(value, dict):
                camera = int(value.get("camera") or index + 1)
                raw_path = value.get("path")
            else:
                camera = index + 1
                raw_path = value
            resolved = Path(str(raw_path or "")).expanduser().resolve()
            if not resolved.is_file():
                raise RuntimeError(f"El clip de CAM {camera} no existe en disco")
            destination = archive / f"cam-{camera}{resolved.suffix}"
            if resolved != destination:
                shutil.copy2(resolved, destination)
            resolved = destination
            angles.append({
                "camera": camera,
                "path": str(resolved),
                "filename": resolved.name,
                "size_bytes": resolved.stat().st_size,
            })
        if not angles:
            raise RuntimeError("El plugin no devolvió ningún ángulo guardado")
        angles.sort(key=lambda row: row["camera"])
        with self._lock:
            payload = self.store.read(self._default())
            marker = next((row for row in payload.get("clips", []) if row.get("id") == marker_id), None)
            if marker is None:
                raise KeyError(marker_id)
            primary = angles[0]
            marker.update({
                "status": "ready",
                "path": primary["path"],
                "filename": primary["filename"],
                "saved_at": _now(),
                "error": "",
                "size_bytes": sum(int(row["size_bytes"]) for row in angles),
                "backend": "multicam-plugin",
                "source_paths": [str(value.get("path") if isinstance(value, dict) else value) for value in saved_paths],
                "angles": angles,
            })
            self.store.write(payload)
            return dict(marker)

    def fail_marker(self, marker_id: str, error: str) -> None:
        with self._lock:
            payload = self.store.read(self._default())
            marker = next((row for row in payload.get("clips", []) if row.get("id") == marker_id), None)
            if marker is not None:
                marker.update({"status": "failed", "error": str(error or "Error al guardar el clip")[:500]})
                self.store.write(payload)

    def set_included(self, clip_id: str, included: bool) -> dict[str, Any]:
        with self._lock:
            payload = self.store.read(self._default())
            clip = next((row for row in payload.get("clips", []) if row.get("id") == clip_id), None)
            if clip is None:
                raise KeyError(clip_id)
            clip["included"] = bool(included)
            self.store.write(payload)
            return dict(clip)

    def set_composition(self, clip_id: str, segments: list[dict[str, Any]], window_start_ms: int = 0) -> dict[str, Any]:
        """Persist a quick multicamera edit for instant replay and highlights."""
        clean: list[dict[str, int]] = []
        for raw in list(segments or [])[:6]:
            camera = max(1, min(16, int(raw.get("camera") or 1)))
            duration = max(1, min(60, int(raw.get("duration_seconds") or 3)))
            speed = int(raw.get("speed_percent") or 100)
            clean.append({"camera": camera, "duration_seconds": duration, "speed_percent": speed if speed in (25, 50, 75, 100) else 100})
        if not clean:
            raise ValueError("Añade al menos un plano a la repetición")
        with self._lock:
            payload = self.store.read(self._default())
            clip = next((row for row in payload.get("clips", []) if row.get("id") == clip_id), None)
            if clip is None:
                raise KeyError(clip_id)
            available = {int(row.get("camera") or 0) for row in clip.get("angles") or []}
            if available and any(row["camera"] not in available for row in clean):
                raise ValueError("La composición usa una cámara no guardada en este evento")
            clip["composition_start_ms"] = max(0, int(window_start_ms))
            clip["composition"] = clean
            self.store.write(payload)
            return dict(clip)

    def media_path(self, item_id: str, angle: int | None = None) -> Path:
        payload = self.store.read(self._default())
        rows = list(payload.get("clips") or []) + list(payload.get("highlights") or [])
        item = next((row for row in rows if row.get("id") == item_id), None)
        if item is None:
            raise KeyError(item_id)
        source_path = item.get("path") or ""
        if angle is not None and item.get("angles"):
            selected = next(
                (row for row in item["angles"] if int(row.get("camera") or 0) == int(angle)),
                None,
            )
            if selected is None:
                raise KeyError(f"{item_id}:cam{angle}")
            source_path = selected.get("path") or ""
        path = Path(str(source_path)).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(path)
        return path

    def delete_video(self, item_id: str, match_id: str) -> dict[str, Any]:
        """Move an exported video to the local trash; never delete source media."""
        with self._export_lock, self._lock:
            payload = self.store.read(self._default())
            row = next((r for r in payload.get("highlights", []) if r.get("id") == item_id and r.get("match_id") == match_id), None)
            if row is None:
                raise KeyError(item_id)
            trash = self.exports_dir / "Papelera" / item_id
            moved = []
            try:
                for key in ("path", "thumbnail"):
                    source = Path(row.get(key) or "").resolve()
                    if not source.is_file():
                        continue
                    if not (source.is_relative_to(self.exports_dir) or source.is_relative_to(self.base_dir / "videos")):
                        raise ValueError("El archivo no pertenece a la carpeta de repeticiones")
                    trash.mkdir(parents=True, exist_ok=True)
                    target = trash / source.name
                    source.replace(target)
                    moved.append({"key": key, "original": str(source), "trash": str(target)})
                payload["highlights"] = [r for r in payload["highlights"] if r.get("id") != item_id]
                payload.setdefault("deleted", []).append({"item": row, "files": moved, "deleted_at": _now()})
                self.store.write(payload)
            except Exception:
                for file in reversed(moved):
                    Path(file["trash"]).replace(file["original"])
                raise
            return {"id": item_id, "recoverable": True}

    def restore_video(self, item_id: str, match_id: str) -> dict[str, Any]:
        with self._export_lock, self._lock:
            payload = self.store.read(self._default())
            deleted = next((r for r in payload.get("deleted", []) if r["item"].get("id") == item_id and r["item"].get("match_id") == match_id), None)
            if deleted is None:
                raise KeyError(item_id)
            item = dict(deleted["item"])
            moved = []
            try:
                for file in deleted["files"]:
                    target = Path(file["original"])
                    while target.exists():
                        target = target.with_name(f"{target.stem}-restaurado-{uuid.uuid4().hex[:8]}{target.suffix}")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    Path(file["trash"]).replace(target)
                    moved.append((target, Path(file["trash"])))
                    item[file["key"]] = str(target)
                item["filename"] = Path(item["path"]).name
                payload.setdefault("highlights", []).insert(0, item)
                payload["deleted"].remove(deleted)
                self.store.write(payload)
            except Exception:
                for target, original in reversed(moved):
                    target.replace(original)
                raise
            return item

    @staticmethod
    def _ffmpeg() -> str | None:
        configured = os.getenv("SECRETARIATPRO_FFMPEG", "").strip()
        candidates = [configured, shutil.which("ffmpeg") or ""]
        if os.name == "nt":
            candidates.extend([r"C:\ffmpeg\bin\ffmpeg.exe", r"C:\Program Files\ffmpeg\bin\ffmpeg.exe"])
        else:
            candidates.extend(["/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg", "/usr/bin/ffmpeg"])
        found = next((candidate for candidate in candidates if candidate and Path(candidate).is_file()), None)
        if found:
            return found
        try:
            import imageio_ffmpeg
            return imageio_ffmpeg.get_ffmpeg_exe()
        except (ImportError, RuntimeError):
            return None

    def _ready_clips(self, match_id: str, clip_ids: list[str] | None) -> list[dict[str, Any]]:
        rows = self.snapshot(match_id).get("clips") or []
        wanted = set(clip_ids or [])
        selected = [
            row for row in reversed(rows)
            if row.get("status") == "ready"
            and (row.get("id") in wanted if wanted else bool(row.get("included", True)))
            and Path(str(row.get("path") or "")).is_file()
        ]
        if not selected:
            raise RuntimeError("Selecciona al menos un clip guardado para crear los highlights")
        return selected

    def _create_highlights(self, match_id: str, clip_ids: list[str] | None = None, title: str = "Highlights", *, saved_events: bool = False) -> dict[str, Any]:
        if saved_events:
            wanted = set(clip_ids or [])
            rows = self.snapshot(match_id)["highlights"]
            clips = [dict(row, composition=[], angles=[]) for row in reversed(rows) if row["id"] in wanted and Path(row["path"]).is_file()]
            if not clips or len(clips) != len(wanted):
                raise ValueError("Selecciona vídeos disponibles del partido actual")
        else:
            clips = self._ready_clips(match_id, clip_ids)
        directory = self.match_directory(match_id)
        export_id = uuid.uuid4().hex
        clean_title = "".join(ch if ch.isalnum() or ch in "-_ " else "" for ch in str(title or "Highlights")).strip()
        clean_title = (clean_title or "Highlights").replace(" ", "_")[:60]
        ffmpeg = self._ffmpeg()
        if not ffmpeg and any(clip.get("composition") for clip in clips):
            raise RuntimeError("FFmpeg no está disponible para guardar cámaras y velocidades")
        if ffmpeg:
            output = directory / f".{export_id}.mp4"
            work_dir = Path(tempfile.mkdtemp(prefix="secretariatpro-highlights-"))
            concat_file = work_dir / "clips.txt"
            prepared: list[Path] = []
            try:
                for clip_index, clip in enumerate(clips):
                    composition = list(clip.get("composition") or [])
                    if composition and clip.get("angles"):
                        angle_paths = {int(row.get("camera") or 0): Path(str(row.get("path") or "")).resolve() for row in clip["angles"]}
                        cursor = float(clip.get("composition_start_ms") or 0) / 1000
                        for segment_index, segment in enumerate(composition):
                            source = angle_paths.get(int(segment.get("camera") or 0))
                            if not source or not source.is_file():
                                raise RuntimeError("Falta uno de los ángulos de la composición")
                            duration = int(segment.get("duration_seconds") or 1)
                            speed = int(segment.get("speed_percent") or 100)
                            tempo = "atempo=0.5,atempo=0.5" if speed == 25 else f"atempo={speed / 100:.4f}"
                            segment_path = work_dir / f"{clip_index:03d}-{segment_index:02d}.mp4"
                            process = subprocess.run([
                                ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-filter_threads", "1",
                                "-ss", str(cursor), "-t", str(duration), "-i", str(source),
                                "-vf", f"setpts={100 / speed:.8f}*(PTS-STARTPTS),scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1",
                                "-af", tempo, "-r", "30", "-c:v", "libx264",
                                "-threads", "2", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-b:a", "192k",
                                "-movflags", "+faststart", str(segment_path),
                            ], capture_output=True, text=True, timeout=180)
                            if process.returncode != 0:
                                raise RuntimeError(process.stderr.strip() or "FFmpeg no pudo preparar la composición")
                            prepared.append(segment_path)
                            cursor += duration
                    else:
                        prepared.append(Path(clip["path"]).resolve())
                with concat_file.open("w", encoding="utf-8") as handle:
                    for path in prepared:
                        safe_path = str(path).replace("'", "'\\''")
                        handle.write(f"file '{safe_path}'\n")
                process = subprocess.run(
                    [
                        ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-filter_threads", "1",
                        "-f", "concat", "-safe", "0", "-i", str(concat_file),
                        *(["-c", "copy"] if all(c.get("composition") and c.get("angles") for c in clips) else ["-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1", "-r", "30", "-c:v", "libx264", "-threads", "2", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-b:a", "192k"]),
                        "-movflags", "+faststart", str(output),
                    ],
                    capture_output=True, text=True, timeout=300,
                )
                if process.returncode != 0:
                    raise RuntimeError(process.stderr.strip() or "FFmpeg no pudo unir los clips")
                method = "ffmpeg-multicam-composition" if any(clip.get("composition") for clip in clips) else "ffmpeg-fullhd-cover"
            finally:
                shutil.rmtree(work_dir, ignore_errors=True)
        else:
            output = directory / f".{export_id}.mp4"
            self._opencv_concat([Path(row["path"]) for row in clips], output)
            method = "opencv-video-only"

        # Only replace the named video after a complete successful export.
        destination = directory / (f"{clean_title}.mp4" if saved_events else f"{clean_title}_{clips[0]['id'][:8]}.mp4")
        output.replace(destination)
        output = destination
        thumbnail = directory / f"{export_id}.jpg"
        if ffmpeg:
            subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-filter_threads", "1", "-i", str(output), "-frames:v", "1", "-vf", "scale=320:-2", str(thumbnail)], capture_output=True, timeout=30)
        event = clips[0]
        sequence = [dict(s) for c in clips for s in c.get("composition", [])]
        result = {
            **{key: event.get(key) for key in ("event_type", "label", "tags", "period", "match_time", "player", "assistant", "team", "event_id")},
            "sequence": sequence,
            "duration_seconds": sum(float(c.get("duration_seconds") or 0) for c in clips) if saved_events else sum(s["duration_seconds"] * 100 / s["speed_percent"] for s in sequence),
            "shot_count": len(sequence),
            "thumbnail": str(thumbnail) if thumbnail.is_file() else "",
            "saved": True,
            "kind": "montage" if saved_events else "event",
            "id": export_id,
            "match_id": str(match_id or ""),
            "title": str(title or "Highlights")[:120],
            "path": str(output.resolve()),
            "filename": output.name,
            "clip_ids": [row["id"] for row in clips],
            "created_at": _now(),
            "size_bytes": output.stat().st_size,
            "method": method,
        }
        with self._lock:
            payload = self.store.read(self._default())
            payload["highlights"] = [row for row in payload.get("highlights", []) if row.get("path") != result["path"]]
            payload["highlights"].insert(0, result)
            # Keep metadata for every saved video; session cleanup only removes raw angles.
            self.store.write(payload)
        return result

    @staticmethod
    def _opencv_concat(paths: list[Path], output: Path) -> None:
        """Portable fallback used when ffmpeg is not installed; video has no audio."""
        try:
            import cv2
        except Exception as exc:  # pragma: no cover - dependency is part of the app
            raise RuntimeError("Instala FFmpeg para generar el vídeo de highlights") from exc

        writer = None
        target_size: tuple[int, int] = (1920, 1080)
        target_fps = 30.0
        frames_written = 0
        try:
            for path in paths:
                capture = cv2.VideoCapture(str(path))
                if not capture.isOpened():
                    capture.release()
                    raise RuntimeError(f"No se puede leer el clip {path.name}")
                if writer is None:
                    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
                    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
                    fps = float(capture.get(cv2.CAP_PROP_FPS) or 30.0)
                    if width <= 0 or height <= 0:
                        capture.release()
                        raise RuntimeError(f"El clip {path.name} no tiene dimensiones válidas")
                    target_fps = fps if 1 <= fps <= 120 else 30.0
                    writer = cv2.VideoWriter(str(output), cv2.VideoWriter_fourcc(*"mp4v"), target_fps, target_size)
                    if not writer.isOpened():
                        raise RuntimeError("No se pudo crear el archivo MP4 de highlights")
                while True:
                    ok, frame = capture.read()
                    if not ok:
                        break
                    height, width = frame.shape[:2]
                    scale = max(target_size[0] / width, target_size[1] / height)
                    resized = cv2.resize(frame, (max(target_size[0], round(width * scale)), max(target_size[1], round(height * scale))))
                    top = max(0, (resized.shape[0] - target_size[1]) // 2)
                    left = max(0, (resized.shape[1] - target_size[0]) // 2)
                    frame = resized[top:top + target_size[1], left:left + target_size[0]]
                    writer.write(frame)
                    frames_written += 1
                capture.release()
        finally:
            if writer is not None:
                writer.release()
        if frames_written == 0 or not output.is_file():
            output.unlink(missing_ok=True)
            raise RuntimeError("Los clips seleccionados no contienen vídeo legible")

    def clear_compositor(self) -> None:
        """Clear session media only; completed videos and their metadata survive."""
        with self._lock:
            payload = self.store.read(self._default())
            payload["clips"] = []
            self.store.write(payload)
            shutil.rmtree(self.base_dir / "clips", ignore_errors=True)
