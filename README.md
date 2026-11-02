# ToSub — MP4 Audio Extraction and English / Chinese Subtitles

A free Python desktop application for Windows, built with **PySide6**, **FFmpeg**, **faster-whisper**, and **deep-translator**. Designed for long videos (for example, a one-hour English interview), with a reproducible **named Conda environment (`sub_env`)**.

## Features

1. **Extract audio:** MP4 (and other video files) → 16 kHz mono WAV.
2. **Speech to English subtitles:** MP4 or audio → timestamped English `.srt` using Whisper.
3. **English to Traditional Chinese subtitles:** English `.srt` → Chinese `.srt`, preserving timestamps.
4. Background workers keep the GUI responsive, with logs and progress indicators.
5. If Google Translate fails on a line, automatically try MyMemory. If both fail, leave the original English line and record it in a separate report instead of aborting the job.
6. Works with paths containing spaces and Unicode characters; output goes into the local `output/` folder.

**Costs:** The code and models can be used without a paid subscription. Whisper transcription and FFmpeg run locally. Subtitle translation uses third-party online services that may impose rate limits or change their availability; there are no guaranteed free quotas.

## Requirements

- Windows 10/11 (64-bit).
- [Miniconda or Anaconda](https://docs.conda.io/en/latest/miniconda.html).
- Internet access for first-time Conda/pip package installation, first-time Whisper model download, and English-to-Chinese translation.
- For CUDA acceleration (optional): an NVIDIA GPU with compatible CUDA 12 cuBLAS and cuDNN 9 libraries. **CPU (`int8`) is the default** and requires no CUDA setup.

## Quick start (Windows)

1. Extract the project ZIP to any directory, such as `C:\tools\tosub`.
2. Run **`build_sub_env.bat`** (double-click, or launch from Anaconda Prompt). This creates or updates the **named** Conda environment `sub_env`, installs dependencies, and verifies imports.
3. Run **`run_app_sub_env.bat`** to launch the GUI.
4. Select your MP4 or audio file. Click **1. Extract Audio (WAV)** if you need an audio file, **2. Speech → English SRT** to generate English subtitles, then **3. English SRT → Chinese SRT** to translate them. You can also browse an existing English SRT and translate it without transcribing.

Note: Step 2 can transcribe MP4 directly. Running Step 1 first is optional.

### Manual installation (Anaconda Prompt / CMD with Conda available)

```bat
cd /d C:\tools\tosub
conda env create -n sub_env -f environment.yml
conda activate sub_env
python -m pip install -r requirements.txt
python verify_install.py
python app.py
```

If `sub_env` already exists, update rather than create:

```bat
conda env update -n sub_env -f environment.yml --prune
conda activate sub_env
python -m pip install -r requirements.txt
```

From any directory, `conda activate sub_env` selects this named environment. No project-specific prefix path is needed.

## Files

```text
tosub/
├── app.py                  # PySide6 GUI
├── processing.py           # FFmpeg, Whisper, subtitle translation
├── environment.yml         # Conda: Python 3.11, PySide6, FFmpeg
├── requirements.txt        # Pip-only packages (no PySide6)
├── build_sub_env.bat       # Create/update + verify the environment
├── run_app_sub_env.bat     # Activate sub_env and launch GUI
├── verify_install.py       # Check imports and FFmpeg
├── README.md               # This document
├── QUICK_START_EN.txt      # Plain-English setup instructions
├── .gitignore
└── output/                 # Auto-created outputs (Git-ignored)
```

## Output example

For a video named `interview.mp4`:

```text
output/
├── interview.wav
├── interview_en.srt
├── interview_zh.srt
└── interview_zh_translation_report.txt
```

All SRT files are saved as UTF-8 with BOM for broad Windows media-player compatibility.

## Accuracy, performance, and privacy

- Whisper models: `tiny`, `base`, `small` (default), `medium`, `large-v3`. Larger models may be more accurate but take longer and use more memory.
- **CPU is the safe default**. CUDA mode requires an external, compatible NVIDIA CUDA runtime; otherwise you may see `cublas64_12.dll is not found` errors.
- Transcript quality is affected by accents, background music, and overlapping speech. Review proper names and technical terms manually.
- Whisper transcription is local, but the selected model is downloaded on first use (from Hugging Face). Google/MyMemory **send subtitle text to online services** for translation; do not use those modes for confidential transcripts without approval.
- Public free translation endpoints can rate-limit or return no result. Untranslated segments are preserved in English and listed in `*_translation_report.txt`; the output is **not guaranteed to be fully Chinese**.
- Output names are based on the input filename; selecting a different file with the same basename can overwrite files in the output folder.

## Troubleshooting

**`EnvironmentFileNotFound`**: Run the command from the folder that contains `environment.yml`, or use `build_sub_env.bat`.

**`ImportError: DLL load failed while importing QtCore`**: PySide6 is installed by **conda-forge**, not pip. Recreate the environment if a previous environment mixed pip and Conda Qt packages. Try using a clean Anaconda Prompt if the PATH has third-party Qt DLLs.

**`cublas64_12.dll not found`**: Select **CPU** in the app. CUDA requires CUDA 12 cuBLAS and cuDNN 9, installed separately.

**Google translation fails on some subtitles**: The tool retries, then uses MyMemory, and if both fail keeps the English original and writes a report. Re-run later if the public service is rate-limiting requests.

**Conda not found when double-clicking `.bat`**: Run the script from Anaconda Prompt. The launchers also look for some standard installation locations.

**Already have a Conda environment named `sub_env`?** The build script updates that named environment. Rename it in `environment.yml` **and both BAT scripts** if it is used by another project.

## GitHub notes

`.gitignore` excludes media files, subtitles, `output/`, Python caches, Conda environments, and credentials. Before publishing, confirm you have permission to share the source code and select a license suitable for your project. No license is automatically granted by this repository.

## Dependencies / upstream projects

- https://github.com/qtproject/pyside-pyside-setup
- https://ffmpeg.org/
- https://github.com/SYSTRAN/faster-whisper
- https://github.com/nidhaloff/deep-translator
- https://github.com/cdown/srt
