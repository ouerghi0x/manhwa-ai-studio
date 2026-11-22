# AI Workflow Guide — Operating Manhwa AI Studio with an AI Agent

This guide provides copy-pasteable prompts, technical standards, and quality-control rules so your AI agent consistently produces broadcast-quality manhwa recaps using `automate_recordingchapters`, `avatarscript`, and `manhwa-publisher`.

---

## 1. Recommended End-to-End Prompt Template

```text
Work on this recorded chapter: <PATH_TO_CHAPTER_FOLDER>

1. Extract all unique panels from chapter-XXX.mp4 and inspect contact sheets to verify NO character faces are cut off at scroll boundaries. Re-extract exact unclipped timestamps if needed.
2. Upscale all panels 4x using Real-ESRGAN (realesrgan-x4plus-anime).
3. Write a high-retention Long script (~3.5-4 min covering all panels, max 4-5s per panel) and a punchy 60s Short script (20 full-bleed 9:16 panels).
4. Synthesize the narration with local Kokoro-82M (voice: am_adam) at clear natural speed (1.00x-1.03x) using emotion tags ([narrator], [ominous], [shock], [hype], [comedy], [whisper], [pause:Xs]) and mix with timed SFX + BGM.
5. Render both videos using AvatarScript (`character "pixel_narrator"` holding `"streamer_mic"`, lip-synced to the voice WAV, with `explode ... fire:true` at peak twists) and clean 1-line lower-third subtitle pills via FFmpeg `libass` (max 4 words Short / max 6 words Long).
6. Generate 50/50 split-screen Long (1920x1080) and Short (1080x1920) thumbnails with a sticker + curved yellow arrow and visually verify every thumbnail and video verification strip.
7. Publish both as Public via `manhwa-publisher`, linking the Short to the Long video with `--related-video-id`.
```

---

## 2. Tagged Kokoro-82M Voice System (ElevenLabs-Style Inline Tags)

Kokoro-82M voice embeddings (`(511, 1, 256)` numpy arrays) can be linearly blended at runtime to morph emotion without sounding robotic:

| Inline Tag | Voice Blend | Speed | Gain | Best Used For |
| :--- | :--- | :---: | :---: | :--- |
| `[narrator]` | `1.00 * am_adam` | `1.00x` | `0.0 dB` | Core storytelling & scene transitions |
| `[ominous]` | `0.84 * am_adam + 0.16 * bm_george` | `0.96x` | `+1.0 dB` | Dark lore, villains, tension |
| `[shock]` | `0.58 * am_adam + 0.42 * am_michael` | `1.04x` | `+1.6 dB` | Plot twists, jaw-drop reveals |
| `[hype]` | `0.68 * am_adam + 0.32 * am_michael` | `1.05x` | `+1.3 dB` | Climax action & CTA hooks |
| `[comedy]` | `0.65 * am_adam + 0.35 * am_michael` | `1.02x` | `+0.6 dB` | Sarcastic roasts & punchlines |
| `[whisper]` | `1.00 * am_adam` | `0.93x` | `-2.5 dB` | Secrets, inner thoughts, suspense |
| `[pause:0.3s]` | Exact silence insertion | — | — | Comedic timing & breath beats |

---

## 3. AvatarScript Integration Patterns

Inside your Python render script, generate a `.ava` file and stream transparent RGBA avatar frames directly into PIL/FFmpeg:

```ava
scene "Chapter_Recap_Short":
    canvas 1440x2560
    background "transparent"
    fps 30
    duration 60.00s
    render "short_ava.mp4"

    avatar "PixelHost":
        character "pixel_narrator"
        position x:1126 y:1993
        scale 1.23
        hold item:"streamer_mic" hand:right scale:1.05

        idle:
            breathe
            blink every 2.8s

        at 0.00s:
            expression smirk
            talk audio:"short_voice_mastered.wav" duration 60.00s threshold:0.09

        at 14.50s:
            expression shocked
            aura red size:76 intensity:2.1 speed:2.3 sparks:1 duration 0.25s
            shake intensity:16 duration 0.32s
            explode duration 2.4s scatter:0.35s separated:1.05s reassemble:1.00s intensity:1.25 fire:true color:"red"
```

Available built-in characters in `avatarscript/assets/characters/`:
`pixel_narrator`, `flame_emperor`, `kenney_host`, `ninja`, `demon`, `streamer`, `gongja`, `jin`, `default`.

---

## 4. Mandatory Visual Quality-Control (QC) Checklist

Before publishing any video with `manhwa-publisher`, instruct the AI agent to inspect rendered verification strips and enforce these rules:

- **Zero Multi-Line Subtitle Blocks:** Never draw large boxed paragraphs with PIL. Always generate bite-sized `.srt` pills (`max_words=4, max_chars=22` for Shorts; `max_words=6, max_chars=38` for Long) burned in via FFmpeg `subtitles=...:force_style='FontName=Segoe UI,BorderStyle=1,Outline=1.3,Shadow=1.6,Alignment=2'`.
- **Zero Clipped Faces:** When extracting panels from a `PageDown` recording, audit a 20-cut preview sheet before rendering. If a head is cut off by a scroll boundary, scrub `±2.0s` in the source recording to grab the unclipped frame.
- **No Black Pillarbox Bars on Thumbnails:** Always use `fit_cover()` (`scale = max(tw / w, th / h)`) on split-screen thumbnails, avoid emoji glyphs in Impact/Arial fonts (prevents `□` missing-glyph boxes), and keep the sticker + curved arrow clear of faces.
- **YouTube Thumbnail API Rate Limit:** YouTube Data API v3 enforces a daily cap on `thumbnails.set` (`HTTP 429 uploadRateLimitExceeded`). Even if thumbnail setting is rate-limited, the video itself uploads completely and can have its custom thumbnail attached in YouTube Studio.
