# AvatarScript Examples Catalog

This folder contains official demonstration `.ava` scripts and code showcasing the full animation, arm control, aura, and prop rigging capabilities of AvatarScript.

---

## 1. Script Showcase (`.ava`)

| Script | Resolution & FPS | Characters | Highlights |
| :--- | :--- | :--- | :--- |
| **[`basic_reaction.ava`](basic_reaction.ava)** | 1280x720 @ 30 FPS | `default` | Minimal starter script: breathing, periodic blinking, and basic expression swaps. |
| **[`anime_reaction.ava`](anime_reaction.ava)** | 1920x1080 @ 30 FPS | `default` | Full 12s reaction timeline: horizontal camera move, shake, bounce, and easing transitions. |
| **[`manhwa_commentary_shorts.ava`](manhwa_commentary_shorts.ava)** | 1080x1920 @ 60 FPS | `default` | High-framerate vertical Shorts/TikTok commentary layout with dynamic zooms and nod gestures. |
| **[`arm_control_and_characters.ava`](arm_control_and_characters.ava)** | 1920x1080 @ 30 FPS | `ninja`, `demon`, `default` | Multi-avatar co-host scene with independent `left_arm` and `right_arm` poses (salutes, combat stances). |
| **[`super_saiyan_aura.ava`](super_saiyan_aura.ava)** | 1920x1080 @ 30 FPS | `ninja` | Dragon Ball Z-style Ki energy charging, Super Saiyan gold transformation, rising flame noise, and electric sparks. |
| **[`prop_rigging_showcase.ava`](prop_rigging_showcase.ava)** | 1920x1080 @ 30 FPS | `default`, `ninja` | Vector prop rigging: holding and swapping microphones, controllers, glowing swords, and phones with custom scaling (`scale:1.4`). |
| **[`lipsync_narration_showcase.ava`](lipsync_narration_showcase.ava)** | 1920x1080 @ 30 FPS | `default` | Audio-driven viseme lip-sync: articulates mouth syllables in exact synchronization with real voiceover audio (`voice_part1.mp3`). |
| **[`depth_25d_showcase.ava`](depth_25d_showcase.ava)** | 1280x720 @ 30 FPS | `default` | 2.5D VTuber depth parallax: differential layer shifts (`head_turn yaw/pitch`), perspective eye/mouth compression, and pupil tracking (`look at:left/right`). |
| **[`flying_showcase.ava`](flying_showcase.ava)** | 1920x1080 @ 30 FPS | `ninja` | Cinematic flight and dynamic size scaling: high-speed flight across canvas, massive scale camera zoom-in (`scale 1.85`), banking tilts (`rotate`), and distance shrinkage (`scale 0.55`). |
| **[`duo_commentary_debate.ava`](duo_commentary_debate.ava)** | 1920x1080 @ 30 FPS | `ninja`, `demon` | Heated conversational debate scene between co-hosts. |
| **[`gaming_rage_popoff.ava`](gaming_rage_popoff.ava)** | 1920x1080 @ 30 FPS | `default` | Sudden gamer rage pop-off with screen shake, elastic zooms, and explosive expressions. |

---

## 2. Directory Layout

- **`*.ava`**: The pure declarative animation source scripts.
- **`snapshots/`**: High-resolution PNG frame grabs exported directly from the renderer verifying visual rig states.
- **`renders/`**: Pre-rendered H.264 `.mp4` video outputs (ignored by Git to keep the repository lightweight).
- **`phase1_demo.py`**: Programmatic Python API demonstration exercising the runtime and rasterizer without compiling DSL text.

---

## 3. How to Run Any Example

### Interactive Live Preview (Pygame):
```powershell
avatarscript preview examples/prop_rigging_showcase.ava
```

### Export to MP4:
```powershell
avatarscript render examples/prop_rigging_showcase.ava -o examples/renders/prop_rigging_showcase.mp4
```

### Export Transparent RGBA PNG Sequence (for Premiere / Resolve / CapCut):
```powershell
avatarscript export-frames examples/super_saiyan_aura.ava -o examples/snapshots/aura_sequence
```
