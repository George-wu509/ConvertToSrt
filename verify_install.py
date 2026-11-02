"""Quick post-installation checks. No model download is triggered."""

import shutil
import sys


def main() -> int:
    print("Python:", sys.executable)
    print("Version:", sys.version.split()[0])
    failures = []
    for module in ("PySide6.QtCore", "PySide6.QtWidgets", "faster_whisper", "srt", "deep_translator", "imageio_ffmpeg"):
        try:
            __import__(module)
            print("[OK]", module)
        except Exception as exc:
            print("[FAIL]", module, "->", repr(exc))
            failures.append(module)

    try:
        from processing import find_ffmpeg
        import subprocess
        ffmpeg = find_ffmpeg()
        subprocess.run([ffmpeg, "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        print("[OK] FFmpeg:", ffmpeg)
    except Exception as exc:
        print("[FAIL] FFmpeg ->", repr(exc))
        failures.append("ffmpeg")

    if failures:
        print("Installation requires attention:", ", ".join(failures))
        return 1
    print("All checks passed. The speech model will download on its first use.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
