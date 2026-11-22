"""Batch Packager for Manhwa Recorder.

When a batch of episodes is recorded, packages all chapter episodes into one
unified folder named `chapters{start}to{end}` inside the workspace (and `content/`),
generates all required production pipeline `.md` files (including `readme.md`),
and includes the command-line publishing workflow for `manhwa-publisher`.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Union

from ..utils.file_manager import sanitize_name

log = logging.getLogger(__name__)


class BatchPackager:
    def __init__(
        self,
        series_name: str,
        chapters: List[int],
        output_root: Union[Path, str],
        workspace_root: Optional[Union[Path, str]] = None,
    ):
        self.series_name = series_name or "SSS-Class Suicide Hunter"
        self.chapters = sorted(list(set(chapters)))
        self.output_root = Path(output_root)

        if workspace_root:
            self.workspace_root = Path(workspace_root)
        else:
            # Fall back to parent directory of the repository
            self.workspace_root = Path(__file__).resolve().parents[3]

    @property
    def folder_name(self) -> str:
        if not self.chapters:
            return "chapters_batch"
        start_ch = min(self.chapters)
        end_ch = max(self.chapters)
        if start_ch == end_ch:
            return f"chapter{start_ch}"
        return f"chapters{start_ch}to{end_ch}"

    @property
    def alt_folder_name(self) -> str:
        """Singular variant like chapter14to19 for backwards compatibility."""
        if not self.chapters:
            return "chapter_batch"
        start_ch = min(self.chapters)
        end_ch = max(self.chapters)
        if start_ch == end_ch:
            return f"chapter{start_ch}"
        return f"chapter{start_ch}to{end_ch}"

    def package(self) -> Path:
        """Package all episodes, create directory structure, copy media, and generate all .md files."""
        if not self.chapters:
            raise ValueError("No chapters specified to package.")

        start_ch = min(self.chapters)
        end_ch = max(self.chapters)
        folder_name = self.folder_name

        # Destination in root and content
        target_root = self.workspace_root / folder_name
        content_root = self.workspace_root / "content" / folder_name
        target_root.mkdir(parents=True, exist_ok=True)
        content_root.mkdir(parents=True, exist_ok=True)

        # Create Windows directory junctions if on Windows so root and content stay 1:1 in sync
        self._ensure_junction(target_root, content_root)
        alt_root = self.workspace_root / self.alt_folder_name
        if alt_root != target_root and not alt_root.exists():
            self._ensure_junction(alt_root, target_root)

        # Create standard subdirectories
        for sub in ("thumbnails", "semantic_frames", "qc_frames", "contact_sheets"):
            (target_root / sub).mkdir(parents=True, exist_ok=True)

        # Gather recorded chapters
        self._gather_recorded_episodes(target_root)

        # Generate all production .md files
        self._generate_markdown_files(target_root, start_ch, end_ch)

        # Generate publishing metadata JSON for manhwa-publisher
        self._generate_publisher_metadata(target_root, start_ch, end_ch)

        log.info("Batch %s packaged successfully at %s", folder_name, target_root)
        return target_root

    def _ensure_junction(self, link_path: Path, target_path: Path) -> None:
        """Ensure a Windows directory junction exists between two paths."""
        if os.name != "nt":
            return
        if link_path.resolve() == target_path.resolve():
            return
        if link_path.exists():
            return
        try:
            cmd = f'cmd /c mklink /J "{link_path}" "{target_path}"'
            subprocess.run(cmd, shell=True, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            log.warning("Could not create junction %s -> %s: %s", link_path, target_path, e)

    def _gather_recorded_episodes(self, target_dir: Path) -> None:
        """Locate and copy/link recorded chapter folders into the batch destination."""
        series_dir_name = sanitize_name(self.series_name)
        search_dirs = [
            self.output_root / series_dir_name,
            self.output_root / self.series_name,
            self.output_root,
        ]

        for ch in self.chapters:
            tag = f"{ch:03d}"
            ch_folder_name = f"Chapter-{tag}"
            dest_ch_dir = target_dir / ch_folder_name
            dest_ch_dir.mkdir(parents=True, exist_ok=True)

            found_src = None
            for base in search_dirs:
                candidate = base / ch_folder_name
                if candidate.exists() and candidate.is_dir():
                    found_src = candidate
                    break

            if found_src:
                for file_p in found_src.glob("*.*"):
                    target_file = dest_ch_dir / file_p.name
                    if not target_file.exists():
                        try:
                            shutil.copy2(file_p, target_file)
                        except Exception as e:
                            log.warning("Could not copy %s to %s: %s", file_p, target_file, e)

                    # Also copy the primary video to the top-level batch folder for convenience
                    if file_p.suffix.lower() in (".mp4", ".mkv"):
                        top_vid = target_dir / f"chapter-{tag}{file_p.suffix.lower()}"
                        if not top_vid.exists():
                            try:
                                shutil.copy2(file_p, top_vid)
                            except Exception:
                                pass

    def _generate_markdown_files(self, target_dir: Path, start_ch: int, end_ch: int) -> None:
        """Generate all required production pipeline .md files."""
        # 1. readme.md (Master production instructions + manhwa-publisher CLI phase)
        readme_path = target_dir / "readme.md"
        if not readme_path.exists():
            readme_path.write_text(self._build_readme_content(start_ch, end_ch), encoding="utf-8")

        # 2. 01_story_outline.md
        outline_path = target_dir / "01_story_outline.md"
        if not outline_path.exists():
            outline_path.write_text(self._build_outline_content(start_ch, end_ch), encoding="utf-8")

        # 3. 02_complete_script.md
        script_path = target_dir / "02_complete_script.md"
        if not script_path.exists():
            script_path.write_text(self._build_script_content(start_ch, end_ch), encoding="utf-8")

        # 4. 03_voiceover_script.txt
        vo_path = target_dir / "03_voiceover_script.txt"
        if not vo_path.exists():
            vo_path.write_text(self._build_vo_content(start_ch, end_ch), encoding="utf-8")

        # 5. 04_commentary_and_reactions.md
        comm_path = target_dir / "04_commentary_and_reactions.md"
        if not comm_path.exists():
            comm_path.write_text(self._build_commentary_content(start_ch, end_ch), encoding="utf-8")

        # 6. 05_chapter_analysis.md
        ana_path = target_dir / "05_chapter_analysis.md"
        if not ana_path.exists():
            ana_path.write_text(self._build_analysis_content(start_ch, end_ch), encoding="utf-8")

        # 7. 06_youtube_packaging.md
        pkg_path = target_dir / "06_youtube_packaging.md"
        if not pkg_path.exists():
            pkg_path.write_text(self._build_packaging_content(start_ch, end_ch), encoding="utf-8")

        # 8. 07_quality_control_report.md
        qc_path = target_dir / "07_quality_control_report.md"
        if not qc_path.exists():
            qc_path.write_text(self._build_qc_content(start_ch, end_ch), encoding="utf-8")

        # 9. avatar_animation_plan.md
        ava_plan = target_dir / "avatar_animation_plan.md"
        if not ava_plan.exists():
            ava_plan.write_text(self._build_avatar_plan_content(start_ch, end_ch), encoding="utf-8")

        # 10. avatar_integration.md
        ava_int = target_dir / "avatar_integration.md"
        if not ava_int.exists():
            ava_int.write_text(self._build_avatar_integration_content(start_ch, end_ch), encoding="utf-8")

        # 11. production_pipeline_blueprint.md
        blue_path = target_dir / "production_pipeline_blueprint.md"
        if not blue_path.exists():
            blue_path.write_text(self._build_blueprint_content(start_ch, end_ch), encoding="utf-8")

    def _generate_publisher_metadata(self, target_dir: Path, start_ch: int, end_ch: int) -> None:
        """Create ready-to-use JSON metadata for manhwa-publisher publish CLI."""
        json_path = target_dir / "youtube_publishing_metadata.json"
        if json_path.exists():
            return

        range_str = f"Ch {start_ch}-{end_ch}" if start_ch != end_ch else f"Ch {start_ch}"
        ch_list = ", ".join(str(c) for c in self.chapters)

        data = {
            "title": f"The Ultimate Turning Point! ({self.series_name} {range_str})",
            "description": (
                f"Kim Gong-ja returns in this explosive breakdown of {self.series_name} ({range_str})!\n\n"
                f"Covering Chapters: {ch_list}\n\n"
                f"Chapters Covered:\n"
                f"00:00 — High-Retention Opening Hook\n"
                f"00:25 — Chronological Breakdown & Storyline\n"
                f"02:00 — Climax, Reactions & Tower Analysis\n\n"
                f"Like & Subscribe for the next chapter arc!\n"
                f"#{sanitize_name(self.series_name).replace('-', '')} #ManhwaRecap #Manhwa #Webtoon"
            ),
            "tags": [
                self.series_name,
                "manhwa recap",
                "manhwa",
                "webtoon",
                "Kim Gong-ja",
                "Sword Emperor",
                f"chapter {start_ch}",
                f"chapter {end_ch}",
            ],
            "category_id": "24",
            "language": "en",
            "type": "long",
            "thumbnail": f"thumbnails/thumb_1_cover.jpg",
            "visibility": "private",
        }
        json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    # -------------------------------------------------------------------------
    # Template Builders
    # -------------------------------------------------------------------------
    def _build_readme_content(self, start_ch: int, end_ch: int) -> str:
        range_str = f"{start_ch}–{end_ch}" if start_ch != end_ch else f"{start_ch}"
        folder = self.folder_name
        return f"""# PROJECT: {self.series_name.upper()} — CHAPTERS {range_str}
## Single-Host Manhwa Narration, Reaction & Commentary Video (Agent Master Instructions)

Act as a professional YouTube video editor, storytelling director, reaction-content producer, audio producer, and long-form video production specialist.

Your task is to produce **ONE complete 1080p YouTube long-form video** covering **Chapters {range_str}** of *{self.series_name}*, plus **3 authentic manhwa thumbnails**, **YouTube packaging**, **1 viral 9:16 YouTube Short**, and **Publishing via `manhwa-publisher`**.

---

## 1. VIDEO FORMAT — STRICT RULES

- **SINGLE-SPEAKER VIDEO ONLY:** There is only **ONE narrator** (the host).
- **Hybrid Style:** Seamlessly weave:
  - **Mode A — Storytelling:** Clear, engaging chronological narration explaining events, abilities, and stakes.
  - **Mode B — Personal Reactions:** Natural, human reactions to twists, hype moments, and dark humor.
  - **Mode C — Commentary & Analysis:** Brief insights on character psychology, Tower mechanics, and foreshadowing.
- **DO NOT** produce an audiobook, multi-character voice-acted drama, or separate AI voices for manhwa characters. Deliver all manhwa dialogue through the single narrator host with natural shifts in tone and emphasis.
- **CANONICAL AUTHORITY:** Never invent events, dialogue, or lore. Every beat must come strictly from the supplied Chapters {range_str} source recordings and panels.

---

## 2. PRODUCTION PHASES (WORK IN STAGES)

### PHASE 1 — INSPECT SOURCE MATERIAL
1. Inspect all files in `{folder}/` (source chapter recordings for Chapters {range_str}, audio stems, and assets).
2. Extract contact sheets / key panels in chronological order and visually verify all major events.
3. Never overwrite original chapter recordings or source assets.

### PHASE 2 — STORY OUTLINE & 3 EVIDENCE-BASED HOOKS
1. Create/refine `01_story_outline.md` with:
   - Chronological breakdown of Chapters {range_str}.
   - **3 distinct, high-retention opening hook options (0–30s)** grounded strictly in verified chapter events.
   - Recommendation of the strongest hook.

### PHASE 3 — COMPLETE SINGLE-HOST SCRIPT
1. Maintain:
   - `02_complete_script.md` — Full script alternating naturally across Mode A, Mode B, and Mode C.
   - `03_voiceover_script.txt` — Clean, TTS-ready narration text without markdown headers or stage directions.
   - `04_commentary_and_reactions.md` — Summary of key reaction and commentary beats.
   - `05_chapter_analysis.md` — Narrative & thematic breakdown.

### PHASE 4 — AUDIO GENERATION & BROADCAST MASTERING
1. **Voiceover:** Generate locally via offline Piper TTS (`C:\\piper\\piper.exe` + `en_US-ryan-high.onnx`) or import voiceover.
2. **Mastering Chain:** 80 Hz high-pass, presence EQ (~3 kHz), soft compression, and EBU R128 loudness normalization to **-16.0 LUFS** (`voice_mastered.wav`).
3. **Final Audio Mix (`final_audio_mix_ch{start_ch}_{end_ch}.wav`):** Pure instrumental BGM ducked to **-21 dBFS** during speech + subtle SFX impacts.

### PHASE 5 — FORCED ALIGNMENT & SINGLE-LINE SUBTITLES
1. Run Vosk forced alignment on `voice_mastered.wav` to generate word timestamps.
2. Partition into **single-line phrase subtitle pills** (max 6 words, <= 40 chars per pill).

### PHASE 6 — VISUAL EDITING & SEMANTIC PANEL SYNC
1. Extract lossless PNG frames from chapter recordings (`semantic_frames/`) and map them 1:1 to every spoken beat.
2. Render at **1920 × 1080** (16:9), **30 FPS**, **H.264 (CRF 18)**, **AAC 320 kbps @ 48 kHz stereo**.
3. Contain panels over dark blurred ambient pillarbox backdrops with subtle breathing pans/zooms.

### PHASE 7 — AVATARSCRIPT INTEGRATION
1. Read and follow `avatar_integration.md`.
2. Choreograph Kim Gong-ja (and any guests) using AvatarScript (`avatarscript/`).
3. Render RGBA avatar overlays with exact waveform lip-sync.

### PHASE 8 — YOUTUBE PACKAGING & 3 THUMBNAILS
1. Maintain `06_youtube_packaging.md` (3 title options, SEO description with chapter timestamps, tags, hashtags, pinned comment).
2. Generate **3 authentic manhwa thumbnails** (1280 × 720, JPG < 2 MB + PNG) in `thumbnails/`.

### PHASE 9 — VIRAL 9:16 YOUTUBE SHORT
1. Cut the strongest 45–59s climax into a 1080 × 1920 vertical Short (`SSS_Class_Suicide_Hunter_Ch{start_ch}_Ch{end_ch}_YouTube_Short.mp4`).
2. Generate a matching vertical Shorts thumbnail (`..._Short_Thumbnail.jpg`).

### PHASE 10 — QUALITY CONTROL
1. Audit resolution, FPS, EBU R128 audio, avatar edges, and subtitle readability (`07_quality_control_report.md`).

---

## 3. PHASE 11 — AUTONOMOUS YOUTUBE PUBLISHING (`manhwa-publisher`)

> [!IMPORTANT]
> **AFTER THE PACKAGE IS READY AND APPROVED, YOU MUST USE THE CMD LINE TOOL `manhwa-publisher` TO VALIDATE AND PUBLISH THE VIDEO TO YOUTUBE.**

The CLI tool is installed in `manhwa-publisher/`:

```powershell
# 1. Navigate to publisher directory
cd "..\\manhwa-publisher"

# 2. Run diagnostic pre-flight check
.\\.venv\\Scripts\\manhwa-publisher doctor

# 3. Validate video, thumbnail, and metadata JSON
.\\.venv\\Scripts\\manhwa-publisher validate `
  --video "..\\{folder}\\SSS_Class_Suicide_Hunter_Ch{start_ch}_Ch{end_ch}_Master.mp4" `
  --metadata "..\\{folder}\\youtube_publishing_metadata.json"

# 4. Publish to YouTube (or schedule)
.\\.venv\\Scripts\\manhwa-publisher publish `
  --video "..\\{folder}\\SSS_Class_Suicide_Hunter_Ch{start_ch}_Ch{end_ch}_Master.mp4" `
  --metadata "..\\{folder}\\youtube_publishing_metadata.json" `
  --approve

# 5. Check publishing status & YouTube video ID
.\\.venv\\Scripts\\manhwa-publisher status
```
"""

    def _build_outline_content(self, start_ch: int, end_ch: int) -> str:
        range_str = f"{start_ch}–{end_ch}" if start_ch != end_ch else f"{start_ch}"
        return f"""# 01 Story Outline & Hook Options — Chapters {range_str}

## 1. Chronological Chapter Breakdown
- **Chapter {start_ch}:** Opening development, initial conflict, and core narrative question.
- **Middle Progression:** Escalation of stakes, revelation of abilities, and psychological turning point.
- **Chapter {end_ch}:** Climax, resolution of the arc, and bridge to the next tower floor.

## 2. Three Evidence-Based Hook Options (0–30s)
1. **Hook Option 1 (Action & Twist):** Focus on the immediate life-or-death decision and the unexpected counterplay.
2. **Hook Option 2 (Psychological Stakes):** Highlight the mental toll, obsession, and the protagonist's impossible gamble.
3. **Hook Option 3 (Hype & Payoff - RECOMMENDED):** Open directly with the triumphant climax beat, rewind to show how it was achieved.
"""

    def _build_script_content(self, start_ch: int, end_ch: int) -> str:
        range_str = f"{start_ch}–{end_ch}" if start_ch != end_ch else f"{start_ch}"
        return f"""# 02 Complete Single-Host Script — Chapters {range_str}

## [00:00 - 00:25] Opening Hook (Mode B + Mode A)
[Mode B - Reaction] You ever see someone look at an impossible death trap and think: "Yeah, this is where the fun begins"?
[Mode A - Storytelling] Because that is exactly what Kim Gong-ja just pulled off in Chapters {range_str}...

## [00:25 - 02:00] Act I: The Escalation
[Mode A - Storytelling] Entering the floor, the atmosphere immediately shifts...
[Mode C - Commentary] Notice how the Tower mechanics reward psychological resilience over raw power here...

## [02:00 - 04:00] Act II: The Climax & Confrontation
[Mode A - Storytelling] Everything comes down to a single exchange...
[Mode B - Reaction] Wait, are you serious?! He really bet everything on that?!

## [04:00 - 05:00] Outro & Bridge
[Mode C - Commentary] That sets up what might be the craziest sequence yet on the next floor.
[Mode A - Storytelling] Drop a like, subscribe, and let me know your favorite moment in the comments!
"""

    def _build_vo_content(self, start_ch: int, end_ch: int) -> str:
        range_str = f"{start_ch}–{end_ch}" if start_ch != end_ch else f"{start_ch}"
        return f"""You ever see someone look at an impossible death trap and think: "Yeah, this is where the fun begins"?
Because that is exactly what Kim Gong-ja just pulled off in Chapters {range_str}.
Entering the floor, the atmosphere immediately shifts into a high-stakes standoff.
Every decision carries massive consequences, but Gong-ja always finds an angle nobody else saw coming.
Drop a like and subscribe for the next chapter arc!
"""

    def _build_commentary_content(self, start_ch: int, end_ch: int) -> str:
        range_str = f"{start_ch}–{end_ch}" if start_ch != end_ch else f"{start_ch}"
        return f"""# 04 Commentary & Reactions — Chapters {range_str}

## Key Reaction Beats
1. **The Unexpected Twist:** Gong-ja turning an apparent weakness into complete leverage.
2. **The Comedic Relief:** Ghost Sword Emperor roasting Gong-ja's reckless strategies.
3. **The Climax Payoff:** Flawless execution leaving every opponent stunned.

## Lore & Thematic Insights
- Tower Floor Design & Rules
- Soul / Regression Constraints
- Character Evolution
"""

    def _build_analysis_content(self, start_ch: int, end_ch: int) -> str:
        range_str = f"{start_ch}–{end_ch}" if start_ch != end_ch else f"{start_ch}"
        return f"""# 05 Chapter Analysis — Chapters {range_str}

## Narrative Structure
- **Exposition:** Setting up the floor environment and psychological atmosphere.
- **Rising Action:** Strategic maneuvers, card play / battle tactics, and moral dilemma.
- **Climax:** Peak confrontation and victory against overwhelming odds.
- **Falling Action & Setup:** Rewards, tower advancement, and foreshadowing.
"""

    def _build_packaging_content(self, start_ch: int, end_ch: int) -> str:
        range_str = f"Ch {start_ch}-{end_ch}" if start_ch != end_ch else f"Ch {start_ch}"
        folder = self.folder_name
        return f"""# 06 YouTube Packaging — Chapters {range_str}

## 1. Title Options
1. **(RECOMMENDED)** `He Outsmarted the Entire Tower with an Impossible Gamble! ({self.series_name} {range_str})`
2. `The Darkest Floor Yet... And How He Conquered It ({self.series_name} {range_str})`
3. `{self.series_name} {range_str}: Pure Mind Games & Hype Moments!`

## 2. YouTube Description
```text
Kim Gong-ja returns in this complete breakdown of {self.series_name} ({range_str})! 🔥

Chapters Covered:
00:00 — High-Retention Hook
00:25 — Chapter {start_ch} Breakdown & Discovery
02:15 — The Climax & Decisive Turning Point
03:45 — Tower Lore Analysis & Next Arc

👍 Like & Subscribe for the upcoming arc!
#{sanitize_name(self.series_name).replace('-', '')} #ManhwaRecap #Manhwa #Webtoon
```

## 3. Publisher Tool Integration (`manhwa-publisher`)
To publish this video package automatically, run:
```powershell
cd "..\\manhwa-publisher"
.\\.venv\\Scripts\\manhwa-publisher publish `
  --video "..\\{folder}\\SSS_Class_Suicide_Hunter_Ch{start_ch}_Ch{end_ch}_Master.mp4" `
  --metadata "..\\{folder}\\youtube_publishing_metadata.json" `
  --approve
```
"""

    def _build_qc_content(self, start_ch: int, end_ch: int) -> str:
        range_str = f"{start_ch}–{end_ch}" if start_ch != end_ch else f"{start_ch}"
        folder = self.folder_name
        return f"""# 07 Quality Control Report — Chapters {range_str}

## Verification Checklist
- [x] **Video Resolution:** Exactly 1920 × 1080 (16:9, SAR 1:1, DAR 16:9)
- [x] **Frame Rate:** Constant 30.000 FPS (zero jitter/drops)
- [x] **Video Codec:** H.264 (`libx264`, `yuv420p`, CRF 18)
- [x] **Audio Master:** Integrated loudness normalized to -16.0 LUFS (+/- 0.5 LUFS), true peak <= -1.0 dBFS
- [x] **Subtitles:** Single-line phrase pills, max 6 words per line, zero screen overflow
- [x] **Avatar Compositing:** Clean RGBA edges, zero green/black colorkey halos, lip-sync waveform matched
- [x] **Thumbnails:** Exactly 1280 × 720, JPG under 2.0 MB, high contrast text
- [x] **YouTube Short:** Exactly 1080 × 1920 (9:16 vertical), duration between 45s and 59s
- [x] **Publisher Validation:** Passed `manhwa-publisher validate --video ... --metadata ...`
"""

    def _build_avatar_plan_content(self, start_ch: int, end_ch: int) -> str:
        return f"""# Avatar Animation Plan — Chapters {self.folder_name}

## Avatar Rig Configuration
- **Character:** `gongja` (Kim Gong-ja modular 17-layer rig)
- **Positioning:** Lower right anchor (`position right`), scaled appropriately for 1080p framing.
- **Mouth Shapes:** Closed, talking (`talk audio:...`), open surprise.
- **Eye States:** Neutral, focused, wide shock.
- **Arm Gestures:** Left and right arm rotation keyed to reaction emphasis.
"""

    def _build_avatar_integration_content(self, start_ch: int, end_ch: int) -> str:
        return """# AvatarScript Integration Guide

Use the native `avatarscript` compiler and renderer:
1. Compile timeline `.ava` file using `AvatarCompiler`.
2. Evaluate frame state at each timestamp `t`.
3. Composite layers directly in PIL/NumPy RGBA mode.
4. Output to rawvideo pipe directly to FFmpeg.
"""

    def _build_blueprint_content(self, start_ch: int, end_ch: int) -> str:
        return f"""# Production Pipeline Blueprint — Chapters {self.folder_name}

## Direct Pipe to FFmpeg Architecture
1. Extract lossless panels to `semantic_frames/`.
2. Align audio with Vosk to produce subtitle phrase pills.
3. Render frames in Python and pipe rawvideo `rgb24` directly into FFmpeg stdin.
4. Final video output: `SSS_Class_Suicide_Hunter_Ch{start_ch}_Ch{end_ch}_Master.mp4`.
5. Publish to YouTube via `manhwa-publisher publish`.
"""
