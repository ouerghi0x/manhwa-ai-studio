# Manhwa Recorder — Automated Manhwa Video Capture

**Manhwa Recorder** is a modular Python desktop application (Windows 10/11) that automates recording manhwa chapters directly from a web browser (Google Chrome or Microsoft Edge) into high-quality MP4 / MKV video recordings for YouTube and social video production workflows.

It orchestrates:
- **Playwright** for browser launching, persistent profile management (cookies/sessions), navigation, and lazy-loading image preloading.
- **FFmpeg** for hardware-assisted and software screen capture (`gdigrab` / tab capture / auto-comic cropping) and H.264 (`libx264`) video encoding.
- **Automatic Scrolling Engine** with configurable scroll keys (`PageDown`, `ArrowDown`, `Space`), delays, profiles, dynamic content detection, and end-of-chapter termination.
- **PySide6 (Qt)** dark desktop GUI with live timers, progress bars, batch chapter queues, automated production packaging, and global hotkeys.

---

## Quick Start (Windows)

### 1. Prerequisites
- **Python 3.11+**
- **FFmpeg** on `PATH` (install via `winget install Gyan.FFmpeg` or `choco install ffmpeg`)

### 2. Installation
```powershell
git clone https://github.com/<your-username>/automate_recordingchapters.git
cd automate_recordingchapters
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r manhwa_recorder/requirements.txt
playwright install chromium
```

### 3. Launch the Application
```powershell
.\.venv\Scripts\python -m manhwa_recorder
```

---

## Features

- **Single & Batch Chapter Recording:** Queue chapter ranges (e.g., `1-10` or `45-48, 50`) with configurable confirmation between chapters.
- **Automatic Output Organization:** Saves each chapter cleanly into `output/<Series-Name>/Chapter-001/` with `chapter-001.mp4`, `metadata.json`, and `recording.log` (never overwrites existing takes).
- **Global Hotkeys:**
  - `Ctrl + Alt + P` — Pause / Resume
  - `Ctrl + Alt + S` — Stop & finalize video
  - `Ctrl + Alt + E` — Emergency stop
- **Batch Packager:** Generates ready-to-use video production markdown specs and `youtube_publishing_metadata.json` compatible with [`manhwa-publisher`](../manhwa-publisher).
- **Standalone `.exe` Packaging:** See [manhwa_recorder/README.md](manhwa_recorder/README.md) for full PyInstaller build instructions and advanced configuration.

---

## Running Tests

```powershell
.\.venv\Scripts\python -m pytest manhwa_recorder/tests -v
```

---

## License

MIT License — see [LICENSE](LICENSE) for details.
