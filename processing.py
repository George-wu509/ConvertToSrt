"""Media extraction, English transcription, and EN -> Traditional Chinese SRT translation.

This module deliberately has no Qt dependencies, so it can be reused from scripts.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from collections import Counter
from datetime import timedelta
from pathlib import Path
from typing import Callable

APP_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = APP_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

LogCallback = Callable[[str], None]
ProgressCallback = Callable[[int], None]


def output_paths(media: Path) -> tuple[Path, Path, Path]:
    """Default output paths for one media file."""
    stem = media.stem
    return (
        OUTPUT_DIR / f"{stem}.wav",
        OUTPUT_DIR / f"{stem}_en.srt",
        OUTPUT_DIR / f"{stem}_zh.srt",
    )


def find_ffmpeg() -> str:
    """Prefer conda's FFmpeg; use PATH and imageio-ffmpeg as fallbacks."""
    conda_prefix = os.environ.get("CONDA_PREFIX")
    if conda_prefix:
        root = Path(conda_prefix)
        for candidate in (
            root / "Library" / "bin" / "ffmpeg.exe",  # Windows conda-forge
            root / "bin" / "ffmpeg",             # macOS/Linux
        ):
            if candidate.is_file():
                return str(candidate)

    path_ffmpeg = shutil.which("ffmpeg")
    if path_ffmpeg:
        return path_ffmpeg

    try:
        import imageio_ffmpeg

        executable = imageio_ffmpeg.get_ffmpeg_exe()
        if executable and Path(executable).is_file():
            return executable
    except Exception:
        pass

    raise FileNotFoundError("FFmpeg was not found. Rebuild sub_env using build_sub_env.bat.")


def _atomic_write(path: Path, contents: str) -> None:
    """Avoid leaving a truncated final output file if writing fails."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(path.name + ".tmp")
    try:
        temp_path.write_text(contents, encoding="utf-8-sig")
        temp_path.replace(path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def extract_audio(
    video_path: Path,
    wav_path: Path,
    log: LogCallback = print,
    progress: ProgressCallback = lambda _: None,
) -> Path:
    """Extract 16 kHz, mono PCM WAV suitable for speech recognition."""
    video_path = Path(video_path)
    wav_path = Path(wav_path)
    if not video_path.is_file():
        raise FileNotFoundError(f"Input video was not found: {video_path}")

    wav_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        find_ffmpeg(), "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(video_path), "-map", "0:a:0", "-vn",
        "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(wav_path),
    ]
    log(f"Extracting audio: {video_path.name}")
    progress(10)
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed (exit code {result.returncode}):\n{result.stderr[-3500:]}")
    if not wav_path.is_file() or wav_path.stat().st_size == 0:
        raise RuntimeError("FFmpeg completed without producing a valid WAV file.")
    progress(100)
    log(f"WAV saved: {wav_path}")
    return wav_path


def transcribe_english(
    media_path: Path,
    srt_path: Path,
    model_name: str = "small",
    device: str = "cpu",
    log: LogCallback = print,
    progress: ProgressCallback = lambda _: None,
) -> Path:
    """Transcribe MP4/audio to time-aligned English .srt subtitles.

    CPU is explicitly selected by default to avoid unintended CUDA DLL loading.
    CUDA is opt-in and requires compatible CUDA 12/cuDNN 9 libraries.
    """
    import srt
    from faster_whisper import WhisperModel

    media_path = Path(media_path)
    srt_path = Path(srt_path)
    if not media_path.is_file():
        raise FileNotFoundError(f"Input media was not found: {media_path}")
    if device not in {"cpu", "cuda"}:
        raise ValueError("device must be 'cpu' or 'cuda'")

    compute_type = "int8" if device == "cpu" else "float16"
    log(f"Loading Whisper model '{model_name}' on {device.upper()} ({compute_type}).")
    log("First use may download the selected model from Hugging Face.")
    progress(2)
    model = WhisperModel(model_name, device=device, compute_type=compute_type)
    progress(5)

    segments, info = model.transcribe(
        str(media_path), language="en", vad_filter=True, beam_size=5,
    )
    duration = float(info.duration or 0)
    log(f"Recognized language: {info.language}; duration: {duration:.1f} seconds.")

    subtitles = []
    for seg in segments:  # Transcription actually happens during iteration.
        text = (seg.text or "").strip()
        if not text:
            continue
        start = max(0.0, float(seg.start))
        end = max(start + 0.05, float(seg.end))
        subtitles.append(
            srt.Subtitle(
                index=len(subtitles) + 1,
                start=timedelta(seconds=start),
                end=timedelta(seconds=end),
                content=text,
            )
        )
        if duration > 0:
            progress(min(99, max(5, round(5 + (end / duration) * 94))))
        if len(subtitles) % 25 == 0:
            log(f"Transcribed {len(subtitles)} segments...")

    if not subtitles:
        raise RuntimeError("No speech segments found. Check that the video contains audible English.")

    _atomic_write(srt_path, srt.compose(subtitles))
    progress(100)
    log(f"English SRT saved: {srt_path} ({len(subtitles)} segments)")
    return srt_path


def _translate_one(
    source: str, google, mymemory,
) -> tuple[str, str, str | None]:
    """Return text, provider, error detail. Never silently claim fallback is Chinese."""
    source = " ".join(source.split())
    if not source:
        return "", "empty", None

    errors: list[str] = []
    for attempt in range(2):
        try:
            translated = google.translate(source)
            if isinstance(translated, str) and translated.strip():
                return translated.strip(), "Google", None
            errors.append("Google returned an empty result")
        except Exception as exc:
            errors.append(f"Google: {type(exc).__name__}: {exc}")
        time.sleep(0.7 + 0.7 * attempt)

    try:
        translated = mymemory.translate(source)
        if isinstance(translated, str) and translated.strip():
            return translated.strip(), "MyMemory", "; ".join(errors)
        errors.append("MyMemory returned an empty result")
    except Exception as exc:
        errors.append(f"MyMemory: {type(exc).__name__}: {exc}")
    return source, "UNTRANSLATED", "; ".join(errors)


def translate_to_chinese(
    english_srt: Path,
    chinese_srt: Path,
    log: LogCallback = print,
    progress: ProgressCallback = lambda _: None,
) -> tuple[Path, str]:
    """Translate English SRT into Traditional Chinese (zh-TW).

    Timing and subtitle order remain unchanged. Failed lines keep their English
    text, and a separate report records those entries for later correction.
    """
    import srt
    from deep_translator import GoogleTranslator, MyMemoryTranslator

    english_srt = Path(english_srt)
    chinese_srt = Path(chinese_srt)
    if not english_srt.is_file():
        raise FileNotFoundError(f"English SRT was not found: {english_srt}")
    subs = list(srt.parse(english_srt.read_text(encoding="utf-8-sig")))
    if not subs:
        raise ValueError("The English SRT is empty or has no valid subtitle entries.")

    google = GoogleTranslator(source="en", target="zh-TW")
    # Some deep-translator versions use different codes for Traditional Chinese.
    # A missing MyMemory locale should not prevent the primary translator from working.
    try:
        mymemory = MyMemoryTranslator(source="en", target="zh-TW")
    except Exception as exc:
        log(f"MyMemory initialization warning: {exc}")
        class UnavailableTranslator:
            def translate(self, _: str) -> str:
                raise RuntimeError("MyMemory zh-TW is not available in this installation")
        mymemory = UnavailableTranslator()

    log(f"Translating {len(subs)} subtitles to Traditional Chinese (zh-TW)...")
    counts: Counter[str] = Counter()
    failed: list[tuple[int, str, str]] = []
    translated_subs = []
    for i, sub in enumerate(subs, start=1):
        original = sub.content.strip()
        translated, source, error_detail = _translate_one(original, google, mymemory)
        counts[source] += 1
        if source == "UNTRANSLATED":
            failed.append((sub.index, original, error_detail or "no response"))

        translated_subs.append(
            srt.Subtitle(
                index=sub.index, start=sub.start, end=sub.end,
                content=translated, proprietary=sub.proprietary,
            )
        )
        progress(round(i / len(subs) * 100))
        if i % 20 == 0 or i == len(subs):
            log(f"Translated {i}/{len(subs)}; untranslated: {len(failed)}")
        # Gentle pacing reduces likelihood of service-side rate limiting.
        if i < len(subs):
            time.sleep(0.18)

    _atomic_write(chinese_srt, srt.compose(translated_subs, reindex=True))
    report_path = chinese_srt.with_name(chinese_srt.stem + "_translation_report.txt")
    lines = [
        f"Input: {english_srt}", f"Output: {chinese_srt}",
        f"Subtitles: {len(subs)}", f"Google translated: {counts['Google']}",
        f"MyMemory translated: {counts['MyMemory']}",
        f"Untranslated (kept in English): {len(failed)}", "",
    ]
    if failed:
        lines.append("Entries needing manual review:")
        for index, original, error in failed:
            lines.extend([f"#{index}: {original}", f"  Error: {error}", ""])
    _atomic_write(report_path, "\n".join(lines) + "\n")

    summary = (
        f"Chinese SRT saved: {chinese_srt}\n"
        f"Google: {counts['Google']}; MyMemory: {counts['MyMemory']}; "
        f"untranslated: {len(failed)}\n"
        f"Translation report: {report_path}"
    )
    log(summary)
    return chinese_srt, summary
