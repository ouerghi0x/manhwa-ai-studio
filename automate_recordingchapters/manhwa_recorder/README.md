# Manhwa Recorder — Automated Manhwa Video Capture

**Manhwa Recorder** is a modular Python desktop application that automates recording manhwa chapters directly from a web browser (Google Chrome or Microsoft Edge) into high-quality MP4 / MKV video recordings for video production workflows.

It orchestrates:
- **Playwright** for browser launching, profile management (cookies/sessions), navigation, and lazy-loading preloading.
- **FFmpeg** for hardware-assisted and software screen capture (Windows `gdigrab` or custom region capture) and x264 video encoding.
- **Automatic Scrolling Engine** with configurable speeds, delays, dynamic content detection, and automated end-of-chapter termination.
- **PySide6 (Qt)** for a dark desktop GUI with live timers, progress bars, batch queues, and global hotkeys.

---

## 1. Prerequisites & Windows Setup

### A. Python Environment
Python 3.11+ is required.

1. Create and activate a virtual environment:
   ```powershell
   cd "automate_recordingchapters"
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install dependencies:
   ```powershell
   pip install -r manhwa_recorder/requirements.txt
   ```

3. Ensure Playwright browsers are available (or standard Chrome/Edge is installed on your PC):
   ```powershell
   playwright install chromium
   ```

### B. FFmpeg Installation
FFmpeg with `gdigrab` and `libx264` enabled is required for Windows screen recording.

#### Option 1: Via Chocolatey (Recommended)
```powershell
choco install ffmpeg
```

#### Option 2: Via Winget
```powershell
winget install Gyan.FFmpeg
```

#### Option 3: Manual Installation
1. Download a build from [gyan.dev/ffmpeg/builds](https://www.gyan.dev/ffmpeg/builds/) (e.g. `ffmpeg-release-essentials.zip`).
2. Extract it to `C:\ffmpeg`.
3. Add `C:\ffmpeg\bin` to your System `PATH`, or specify the path directly inside Manhwa Recorder's **Advanced Settings**.

Verify in PowerShell:
```powershell
ffmpeg -version
```

---

## 2. Launching the Application

Run from the `automate_recordingchapters` root directory:
```powershell
.\.venv\Scripts\python -m manhwa_recorder
```
Or directly:
```powershell
cd manhwa_recorder
..\.venv\Scripts\python main.py
```

---

## 3. Workflow & Usage Guide

### Single Chapter Recording
1. **Configure Project:**
   - **Manhwa name:** e.g. `SSS-Class Suicide Hunter`
   - **Chapter number:** e.g. `7`
   - **URL template:** e.g. `https://asurascans.com/comics/sss-class-suicide-hunter-7ba78ec7/chapter/{chapter}`
   - **Chapter URL:** Auto-filled or paste an explicit chapter link.
2. **Browser Controls:**
   - Click **Launch browser** to start Chrome/Edge with your dedicated profile (preserves logins and cookies).
   - Click **Open chapter** to navigate to the chapter.
   - Click **Preload images** (optional) to scroll through once and trigger all lazy-loaded images before returning to top.
3. **Capture & Scroll Settings:**
   - Choose resolution (default: `1920x1080`), FPS (`30`), quality CRF (`18`), and scroll profile (`Slow`, `Normal`, `Fast`, or `Custom`).
4. **Recording:**
   - Click **● Start Recording**.
   - An initial delay (default: 5.0s) allows you to focus the window or adjust zoom.
   - The application automatically sends scroll keys (default: `PageDown`) at configured intervals.
   - Automatically stops when the end of the chapter is detected (or stop manually with **■ Stop**).
   - The finalized video and `metadata.json` will be saved under `output/<Manhwa-Name>/Chapter-<Number>/`.

### Batch Recording & Automated Packaging
1. Click **Add chapters…** under the Batch recording section.
2. Input a range (e.g. `14-19` or `45-48, 50`) or explicit lines of chapter numbers and URLs.
3. Click **Start batch**.
4. The first chapter opens in the browser. Confirm reader readiness, then click **Record this chapter ▶** (or enable auto-continue in Advanced Settings).
5. When finished, the app automatically transitions to the next chapter in the queue.
6. **Automatic Package Creation:** Upon batch completion (or clicking **📦 Package chaptersXtoY**):
   - All recorded chapter folders and videos are gathered into a unified directory in the workspace: `chapters{X}to{Y}/` (e.g. `chapters14to19/`).
   - All required video production markdown specifications (`readme.md`, `01_story_outline.md`, `02_complete_script.md`, `06_youtube_packaging.md`, `07_quality_control_report.md`, `avatar_animation_plan.md`, etc.) are generated automatically.
   - Ready-to-use YouTube publishing metadata (`youtube_publishing_metadata.json`) is created for autonomous YouTube upload.
   - **Publishing with `manhwa-publisher`:** Once video rendering is finalized, run the CLI tool in `manhwa-publisher/`:
     ```powershell
     cd "..\manhwa-publisher"
     .\.venv\Scripts\manhwa-publisher validate --video "..\chapters14to19\SSS_Class_Suicide_Hunter_Ch14_Ch19_Master.mp4" --metadata "..\chapters14to19\youtube_publishing_metadata.json"
     .\.venv\Scripts\manhwa-publisher publish --video "..\chapters14to19\SSS_Class_Suicide_Hunter_Ch14_Ch19_Master.mp4" --metadata "..\chapters14to19\youtube_publishing_metadata.json" --approve
     ```

### Global Hotkeys
Works even when the browser window has focus:
- `Ctrl + Alt + P`: Pause / Resume recording & scrolling
- `Ctrl + Alt + S`: Stop recording gracefully and finalize video
- `Ctrl + Alt + E`: Emergency stop

---

## 4. Output Organization & Metadata

Each chapter is stored in its own dedicated directory:
```
output/
└── SSS-Class-Suicide-Hunter/
    └── Chapter-007/
        ├── chapter-007.mp4
        ├── metadata.json
        └── recording.log
```

If a file with the same name already exists, `-take2`, `-take3`, etc. are safely appended to prevent accidental overwrites.

### Example `metadata.json`:
```json
{
  "series_name": "SSS-Class Suicide Hunter",
  "chapter_number": 7,
  "source_url": "https://asurascans.com/comics/sss-class-suicide-hunter-7ba78ec7/chapter/7",
  "output_filename": "chapter-007.mp4",
  "resolution": "1920x1080",
  "fps": 30,
  "duration_seconds": 128.45,
  "scroll_count": 52,
  "encoding": {
    "codec": "libx264",
    "crf": 18,
    "preset": "veryfast",
    "pix_fmt": "yuv420p",
    "container": "mp4",
    "capture_mode": "browser"
  },
  "scroll_settings": {
    "key": "PageDown",
    "delay": 2.5,
    "initial_delay": 5.0,
    "profile": "Normal"
  },
  "end_reason": "end of chapter detected",
  "file_size_bytes": 145829102,
  "recording_date": "2026-11-18T04:22:00+01:00",
  "app": "Manhwa Recorder 1.0"
}
```

---

## 5. Standalone Windows Executable (.exe) with PyInstaller

To bundle Manhwa Recorder into a portable Windows executable:

1. Install PyInstaller in your virtual environment:
   ```powershell
   pip install pyinstaller
   ```

2. Run PyInstaller from `automate_recordingchapters`:
   ```powershell
   pyinstaller --noconfirm --onedir --windowed `
     --name "ManhwaRecorder" `
     --add-data "manhwa_recorder/sample;sample" `
     --collect-all "playwright" `
     --collect-all "PySide6" `
     manhwa_recorder/main.py
   ```

3. The generated executable will be in `dist/ManhwaRecorder/ManhwaRecorder.exe`.
   *(Note: Ensure FFmpeg is either on the user's system PATH or placed alongside the executable).*

---

## 6. Running Tests & Validation

Run all unit tests:
```powershell
.\.venv\Scripts\python -m pytest manhwa_recorder/tests -v
```

Run the complete browser + scrolling + video encoding End-to-End test on the local mock chapter:
```powershell
.\.venv\Scripts\python manhwa_recorder/tests/e2e_sample.py --testsrc chrome
```
*(Omit `--testsrc` when running directly on an active unlocked Windows desktop session to test live screen capture).*
