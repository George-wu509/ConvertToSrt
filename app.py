"""ToSub: a small Windows-friendly PySide6 desktop subtitles tool."""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit,
    QProgressBar, QPushButton, QVBoxLayout, QWidget,
)

from processing import OUTPUT_DIR, extract_audio, output_paths, transcribe_english, translate_to_chinese

APP_DIR = Path(__file__).resolve().parent
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v"}


class JobThread(QThread):
    progress_changed = Signal(int)
    log_message = Signal(str)
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, task: Callable) -> None:
        super().__init__()
        self.task = task

    def run(self) -> None:
        try:
            result = self.task(self.log_message.emit, self.progress_changed.emit)
            self.succeeded.emit(result)
        except Exception:
            self.failed.emit(traceback.format_exc())


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ToSub | Audio Extraction & Subtitle Generator")
        self.resize(990, 680)
        self.media_path: Path | None = None
        self.english_srt_path: Path | None = None
        self.worker: JobThread | None = None
        self._setup_ui()
        self._log(f"Output folder: {OUTPUT_DIR}")
        self._log("Default transcription device: CPU (int8).")

    def _setup_ui(self) -> None:
        root = QWidget(self)
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("ToSub — Video → WAV → English SRT → Chinese SRT")
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        layout.addWidget(title)
        subtitle = QLabel(
            "Steps are independent: select a video/audio file, extract WAV if needed, "
            "transcribe English, then translate the SRT to Traditional Chinese."
        )
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        inputs = QGroupBox("Input files")
        grid = QGridLayout(inputs)
        self.media_edit = QLineEdit()
        self.media_edit.setReadOnly(True)
        self.media_edit.setPlaceholderText("Choose an MP4, other video, or audio file")
        self.en_edit = QLineEdit()
        self.en_edit.setReadOnly(True)
        self.en_edit.setPlaceholderText("Generated automatically, or choose an existing English .srt")
        output_edit = QLineEdit(str(OUTPUT_DIR))
        output_edit.setReadOnly(True)
        self.media_browse = QPushButton("Browse Media...")
        self.srt_browse = QPushButton("Browse English SRT...")
        self.media_browse.clicked.connect(self._pick_media)
        self.srt_browse.clicked.connect(self._pick_english_srt)
        grid.addWidget(QLabel("Media"), 0, 0)
        grid.addWidget(self.media_edit, 0, 1)
        grid.addWidget(self.media_browse, 0, 2)
        grid.addWidget(QLabel("English SRT"), 1, 0)
        grid.addWidget(self.en_edit, 1, 1)
        grid.addWidget(self.srt_browse, 1, 2)
        grid.addWidget(QLabel("Output folder"), 2, 0)
        grid.addWidget(output_edit, 2, 1, 1, 2)
        layout.addWidget(inputs)

        settings = QGroupBox("Transcription settings")
        settings_row = QHBoxLayout(settings)
        settings_row.addWidget(QLabel("Whisper model"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "base", "small", "medium", "large-v3"])
        self.model_combo.setCurrentText("small")
        settings_row.addWidget(self.model_combo)
        settings_row.addWidget(QLabel("Device"))
        self.device_combo = QComboBox()
        self.device_combo.addItem("CPU (recommended; no CUDA needed)", "cpu")
        self.device_combo.addItem("NVIDIA CUDA GPU (advanced)", "cuda")
        settings_row.addWidget(self.device_combo)
        settings_row.addStretch(1)
        layout.addWidget(settings)

        actions = QGroupBox("Actions")
        actions_row = QHBoxLayout(actions)
        self.audio_btn = QPushButton("1. Extract Audio (WAV)")
        self.en_btn = QPushButton("2. Speech → English SRT")
        self.zh_btn = QPushButton("3. English SRT → Chinese SRT")
        self.folder_btn = QPushButton("Open Output")
        for btn in (self.audio_btn, self.en_btn, self.zh_btn, self.folder_btn):
            btn.setMinimumHeight(40)
            actions_row.addWidget(btn)
        self.audio_btn.clicked.connect(self._start_extract)
        self.en_btn.clicked.connect(self._start_transcribe)
        self.zh_btn.clicked.connect(self._start_translate)
        self.folder_btn.clicked.connect(self._open_output)
        layout.addWidget(actions)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        layout.addWidget(self.progress)
        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        layout.addWidget(QLabel("Activity log"))
        layout.addWidget(self.log_box, 1)

    def _log(self, message: str) -> None:
        self.log_box.appendPlainText(message)

    def _error(self, message: str) -> None:
        self._log("ERROR:\n" + message)
        QMessageBox.critical(self, "ToSub Error", message[-1400:])

    def _pick_media(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self, "Select media file", str(APP_DIR),
            "Media files (*.mp4 *.mkv *.mov *.avi *.webm *.m4v *.wav *.mp3 *.m4a *.flac);;All files (*)",
        )
        if not selected:
            return
        self.media_path = Path(selected)
        self.media_edit.setText(selected)
        _, generated_en, _ = output_paths(self.media_path)
        self.english_srt_path = generated_en if generated_en.exists() else None
        self.en_edit.setText(str(self.english_srt_path) if self.english_srt_path else "")
        self._log(f"Selected media: {selected}")

    def _pick_english_srt(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self, "Select English SRT", str(OUTPUT_DIR), "SRT subtitles (*.srt)"
        )
        if selected:
            self.english_srt_path = Path(selected)
            self.en_edit.setText(selected)
            self._log(f"Selected English SRT: {selected}")

    def _open_output(self) -> None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(str(OUTPUT_DIR))
        else:
            import subprocess
            subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(OUTPUT_DIR)])

    def _require_media(self) -> Path | None:
        if self.media_path is None or not self.media_path.is_file():
            self._error("Please select a valid video or audio file first.")
            return None
        return self.media_path

    def _set_busy(self, busy: bool) -> None:
        for control in (
            self.audio_btn, self.en_btn, self.zh_btn,
            self.media_browse, self.srt_browse, self.model_combo, self.device_combo,
        ):
            control.setEnabled(not busy)

    def _start_task(self, description: str, task: Callable, on_success: Callable) -> None:
        if self.worker is not None:
            self._error("Another task is already running.")
            return
        self._log("\nStarting: " + description)
        self.progress.setValue(0)
        worker = JobThread(task)
        self.worker = worker
        self._set_busy(True)
        worker.log_message.connect(self._log)
        worker.progress_changed.connect(self.progress.setValue)
        worker.succeeded.connect(on_success)
        worker.failed.connect(self._error)
        worker.finished.connect(self._on_task_finished)
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def _on_task_finished(self) -> None:
        self.worker = None
        self._set_busy(False)

    def _start_extract(self) -> None:
        media = self._require_media()
        if media is None:
            return
        if media.suffix.lower() not in VIDEO_EXTENSIONS:
            self._error("Extract Audio expects a video file (MP4/MKV/MOV/AVI/WebM).")
            return
        wav_path, _, _ = output_paths(media)
        self._start_task(
            "Extract WAV", lambda log, progress: extract_audio(media, wav_path, log, progress),
            lambda result: self._log(f"Finished. Audio: {result}"),
        )

    def _start_transcribe(self) -> None:
        media = self._require_media()
        if media is None:
            return
        _, en_path, _ = output_paths(media)
        device = self.device_combo.currentData()
        model = self.model_combo.currentText()
        if device == "cuda":
            yes = QMessageBox.question(
                self, "CUDA Requirements",
                "CUDA mode requires a compatible NVIDIA GPU, CUDA 12 cuBLAS and cuDNN 9. "
                "If you have not installed them, select CPU instead. Continue?",
            )
            if yes != QMessageBox.StandardButton.Yes:
                return
        # Faster-whisper can read MP4 directly; audio extraction is optional.
        self._start_task(
            "English transcription",
            lambda log, progress: transcribe_english(media, en_path, model, device, log, progress),
            self._transcribe_completed,
        )

    def _transcribe_completed(self, path: Path) -> None:
        self.english_srt_path = Path(path)
        self.en_edit.setText(str(path))
        self._log(f"Finished. English SRT: {path}")

    def _start_translate(self) -> None:
        if self.english_srt_path is None or not self.english_srt_path.is_file():
            if self.media_path is not None:
                _, possible, _ = output_paths(self.media_path)
                if possible.is_file():
                    self.english_srt_path = possible
                    self.en_edit.setText(str(possible))
        if self.english_srt_path is None or not self.english_srt_path.is_file():
            self._error("Please generate English subtitles or browse for an English .srt file.")
            return
        english_path = self.english_srt_path
        base_stem = english_path.stem
        if base_stem.endswith("_en"):
            base_stem = base_stem[:-3]
        chinese_path = OUTPUT_DIR / f"{base_stem}_zh.srt"
        self._start_task(
            "Translate subtitles (Traditional Chinese)",
            lambda log, progress: translate_to_chinese(english_path, chinese_path, log, progress),
            self._translate_completed,
        )

    def _translate_completed(self, outcome: tuple[Path, str]) -> None:
        _, summary = outcome
        QMessageBox.information(self, "Translation finished", summary)

    def closeEvent(self, event) -> None:
        if self.worker is not None and self.worker.isRunning():
            QMessageBox.warning(
                self, "Task in progress",
                "Please let the current task finish before closing this window."
            )
            event.ignore()
        else:
            event.accept()


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
