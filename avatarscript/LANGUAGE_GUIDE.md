# AvatarScript v0.1 — Official User Guide & Language Reference

Welcome to **AvatarScript**, a declarative Domain-Specific Language (DSL) and animation engine for building 2D animated reaction avatars, VTuber-style narrators, and commentary overlays for YouTube videos, anime reactions, and manhwa recaps.

Instead of manually keyframing every blink, mouth swap, bounce, or zoom in Premiere Pro / After Effects / CapCut, you write human-readable `.ava` scripts and render them directly into **1080p/60fps MP4 videos** or **transparent RGBA PNG sequences**.

---

## Table of Contents

1. [Installation & Setup](#1-installation--setup)
2. [5-Minute Quickstart](#2-5-minute-quickstart)
3. [Running in VS Code Without the Command Line (One-Click UI)](#3-running-in-vs-code-without-the-command-line-one-click-ui)
4. [CLI Command Reference](#4-cli-command-reference)
4. [The `.ava` Language Guide](#4-the-ava-language-guide)
   - [4.1 Lexical & Syntax Rules](#41-lexical--syntax-rules)
   - [4.2 The `scene` Block](#42-the-scene-block)
   - [4.3 The `avatar` Block & Initial Rig Setup](#43-the-avatar-block--initial-rig-setup)
   - [4.4 Automatic `idle` Behaviors](#44-automatic-idle-behaviors)
   - [4.5 Timeline Blocks (`at <time>s:`)](#45-timeline-blocks-at-times)
   - [4.6 Facial Expressions](#46-facial-expressions)
   - [4.7 Animations & Transform Channels](#47-animations--transform-channels)
   - [4.8 2.5D VTuber Depth System (`head_turn` & `look`)](#48-25d-vtuber-depth-system-head_turn--look)
   - [4.9 Easing Functions](#49-easing-functions)
   - [4.10 Simultaneous & Overlapping Animations](#410-simultaneous--overlapping-animations)
5. [Real-World Production Recipes](#5-real-world-production-recipes)
   - [Recipe 1: YouTube 16:9 Commentary Overlay](#recipe-1-youtube-169-commentary-overlay)
   - [Recipe 2: Vertical 9:16 Manhwa Shorts Narrator (60 FPS)](#recipe-2-vertical-916-manhwa-shorts-narrator-60-fps)
   - [Recipe 3: Multi-Avatar Co-Host Reaction Scene](#recipe-3-multi-avatar-co-host-reaction-scene)
   - [Recipe 4: Cinematic Flight & Dynamic Scale Control](#recipe-4-cinematic-flight--dynamic-scale-control)
6. [Creating Custom SVG Characters](#6-creating-custom-svg-characters)
7. [Compiler Diagnostics & Troubleshooting](#7-compiler-diagnostics--troubleshooting)
8. [Formal Grammar Summary](#8-formal-grammar-summary)

---

## 1. Installation & Setup

AvatarScript runs in its own isolated Python virtual environment located at `avatarscript\.venv`.

```powershell
# From the repository root (c:\Users\wergh\Desktop\sss class suici)
& "avatarscript\.venv\Scripts\avatarscript.exe" --help
```

If setting up on a fresh machine:

```powershell
python -m venv avatarscript\.venv
& "avatarscript\.venv\Scripts\pip.exe" install -r avatarscript\requirements.txt
& "avatarscript\.venv\Scripts\pip.exe" install -e avatarscript --no-deps
```

---

## 2. 5-Minute Quickstart

### Step 1: Create a script (`my_first_avatar.ava`)

```ava
# My first animated reaction avatar
scene "my_first_reaction":

    canvas 1920x1080
    background "#1e1e2e"
    fps 30
    duration 6s

    avatar "host":
        character "default"
        position right
        scale 1.2

        idle:
            breathe
            blink every 3.5s

        at 0s:
            expression neutral

        at 1.5s:
            expression surprised
            animate bounce duration 0.5s easing ease_out

        at 3.5s:
            expression happy
            move x:-100 y:0 duration 0.6s easing ease_in_out

    render "my_first_reaction.mp4"
```

### Step 2: Validate your script
```powershell
& "avatarscript\.venv\Scripts\avatarscript.exe" validate my_first_avatar.ava
```

### Step 3: Preview in real time
```powershell
& "avatarscript\.venv\Scripts\avatarscript.exe" preview my_first_avatar.ava
```

### Step 4: Render to MP4 video
```powershell
& "avatarscript\.venv\Scripts\avatarscript.exe" render my_first_avatar.ava
```

---

## 3. Running in VS Code Without the Command Line (One-Click UI)

With the official **AvatarScript VS Code / Antigravity Extension** installed, you never need to open a terminal to preview, validate, or render `.ava` files.

*(If you haven't reloaded your window after installing the extension, press `Ctrl+Shift+P` → **`Developer: Reload Window`** once.)*

### 3.1 Top-Right Editor Action Buttons
When any `.ava` file is open in your editor, look at the **top-right corner of the editor tab bar**:
- Click **`▶` (Live Preview)** — Saves your file and opens the interactive Pygame preview window immediately.
- Click **`🎥` (Render to MP4 Video)** — Renders your `.ava` file to an H.264 `.mp4` video and shows a progress notification.

### 3.2 Bottom Status Bar Buttons
At the bottom-left of your VS Code window, two one-click buttons appear whenever an `.ava` file is active:
- **`▶ Preview .ava`** — Launches the real-time preview window.
- **`🎥 Render MP4`** — Exports the MP4 video.

### 3.3 Right-Click Context Menu (Editor & File Explorer)
Right-click anywhere inside an `.ava` file (or right-click an `.ava` file in the Explorer sidebar) to access all 4 actions:
1. **`AvatarScript: Live Preview (.ava)`**
2. **`AvatarScript: Render to MP4 Video`**
3. **`AvatarScript: Export Transparent PNG Frames`** *(automatically saves 32-bit RGBA PNGs into a `<script_name>_frames/` folder next to your script)*
4. **`AvatarScript: Validate Script`**

### 3.4 Keyboard Shortcuts
- **`Ctrl+Alt+P`** (`Cmd+Alt+P` on Mac) → Launch Live Preview
- **`Ctrl+Alt+R`** (`Cmd+Alt+R` on Mac) → Render to MP4 Video

### 3.5 Automatic Error Squiggles on Save (`Ctrl+S`)
Every time you press `Ctrl+S` on an `.ava` file, the extension validates your code in the background. Any syntax or semantic mistake is underlined with **red squiggly lines** on the exact line and listed in the VS Code **Problems** panel.

---

## 4. CLI Command Reference

The `avatarscript` CLI provides four primary commands:

### 3.1 `validate`
Parses and semantically validates an `.ava` file without rendering frames. Checks character asset folders, duplicate properties, timeline bounds, expression names, and animation parameters.

```powershell
& "avatarscript\.venv\Scripts\avatarscript.exe" validate avatarscript\examples\anime_reaction.ava
```

### 3.2 `preview`
Opens an interactive real-time **Pygame** preview window.

```powershell
& "avatarscript\.venv\Scripts\avatarscript.exe" preview avatarscript\examples\anime_reaction.ava
```

**Keyboard Shortcuts inside the Preview Window:**
| Key | Action |
| :--- | :--- |
| **`SPACE`** | Toggle Play / Pause |
| **`R`** | Restart playback from `0.00s` |
| **`LEFT ARROW`** | Scrub backward by `0.5s` |
| **`RIGHT ARROW`** | Scrub forward by `0.5s` |
| **`ESC`** | Close preview window |

*(Optional flag: `--max-seconds 5` automatically closes the preview window after 5 seconds.)*

### 3.3 `render`
Renders the `.ava` scene directly to an **H.264 (`yuv420p`) MP4 video** using FFmpeg.

```powershell
# Uses the output filename declared in `render "..."` inside the .ava file:
& "avatarscript\.venv\Scripts\avatarscript.exe" render avatarscript\examples\anime_reaction.ava

# Or override the output path with -o / --output:
& "avatarscript\.venv\Scripts\avatarscript.exe" render avatarscript\examples\anime_reaction.ava -o custom_output.mp4
```

### 3.4 `export-frames`
Exports every frame as a numbered `.png` image (`frame_00000.png`, `frame_00001.png`, ...). By default, frames are exported as **32-bit transparent RGBA PNGs** (ignoring the scene's `background` color) so you can drop them directly on top of your video timeline in Premiere Pro, DaVinci Resolve, CapCut, or MoviePy.

```powershell
# Export transparent RGBA PNG sequence:
& "avatarscript\.venv\Scripts\avatarscript.exe" export-frames avatarscript\examples\basic_reaction.ava -o output_frames

# Export opaque PNG sequence (bakes the scene background color into each PNG):
& "avatarscript\.venv\Scripts\avatarscript.exe" export-frames avatarscript\examples\basic_reaction.ava -o output_frames --opaque
```

---

## 4. The `.ava` Language Guide

### 4.1 Lexical & Syntax Rules

1. **Indentation-Based Blocks**: Like Python, AvatarScript uses **4-space indentation** and colons (`:`) to open blocks (`scene`, `avatar`, `idle:`, `at <time>s:`).
2. **Comments**: Any text following `#` on a line is ignored as a comment.
3. **Time Literals (`TIME`)**: Written as a number followed immediately by `s` (seconds), supporting integers and decimals:
   - Valid: `0s`, `3s`, `0.4s`, `5.75s`, `12.5s`
   - Invalid: `3` (missing `s`), `300ms` (use `0.3s` instead)
4. **Resolution Literals (`RESOLUTION`)**: Written as `<width>x<height>` with no spaces around `x`:
   - Valid: `1920x1080`, `1080x1920`, `1280x720`, `3840x2160`
5. **Strings (`STRING`)**: Double-quoted strings (`"default"`, `"#202020"`, `"output.mp4"`).

---

### 4.2 The `scene` Block

Every `.ava` file contains exactly one top-level `scene "<name>":` block.

```ava
scene "episode_01_intro":

    canvas 1920x1080        # Resolution (default: 1920x1080)
    background "#202020"    # Hex color #RGB, #RRGGBB, or #RRGGBBAA (default: "#202020")
    fps 30                  # Frame rate: 1 to 240 (default: 30)
    duration 12s            # Total duration in seconds (default: 10s, must be > 0s)

    # One or more avatar blocks go here...

    render "output.mp4"     # Default MP4 output filename
```

**Scene Validation Rules:**
- Each scene property (`canvas`, `background`, `fps`, `duration`, `render`) may be declared at most once per scene.
- A scene must contain **at least one** `avatar` block.

---

### 4.3 The `avatar` Block & Initial Rig Setup

You can define one or multiple avatars in a scene. Each avatar has a unique string identifier (`avatar "main":`) and initial transform properties:

```ava
    avatar "main":
        character "default"         # REQUIRED: folder name under assets/characters/
        position right              # Named preset OR explicit x/y coordinates
        scale 1.2                   # Initial size multiplier (default: 1.0, must be > 0)
        rotation 0                  # Initial clockwise angle in degrees (default: 0)
```

#### Positioning Options (`position`)
You can position an avatar using either a **named preset** or **exact pixel coordinates** `(x, y)` representing the center anchor of the avatar rig:

1. **Named Presets** (automatically adapt to any canvas resolution):
   - `position left` → $(25\% \text{ width},\ 62\% \text{ height})$ — e.g. `(480, 670)` on `1920x1080`
   - `position center` → $(50\% \text{ width},\ 62\% \text{ height})$ — e.g. `(960, 670)` on `1920x1080`
   - `position right` → $(75\% \text{ width},\ 62\% \text{ height})$ — e.g. `(1440, 670)` on `1920x1080`
2. **Explicit Pixel Coordinates** (`x:<num> y:<num>`):
   ```ava
   position x:1520 y:720
   ```

---

### 4.4 Automatic `idle` Behaviors

An optional `idle:` block inside an `avatar` keeps the character alive across the entire scene without manual keyframes:

```ava
        idle:
            breathe
            blink every 4s
```

- **`breathe`**: Applies a continuous, subtle sinusoidal vertical motion and chest/head expansion ($\approx 2.8\text{s}$ cycle) to the character's `body`, `head`, `eyes`, and `mouth` layers.
- **`blink` / `blink every <N>s`**: Automatically closes the avatar's eyes (`eyes_closed.svg`) for `0.15s` at the end of every $N$-second cycle. If `every <N>s` is omitted (`blink`), it defaults to `4.0s`. The interval must be `> 0.15s`.

---

### 4.5 Timeline Blocks (`at <time>s:`)

Timeline blocks schedule facial expression changes and animations at exact timestamps (in seconds).

```ava
        at 0s:
            expression neutral

        at 3.2s:
            expression shocked
            animate shake duration 0.4s intensity 16
            scale 1.35 duration 0.3s easing ease_out
```

**Timeline Rules:**
- Timestamps must be $\ge 0\text{s}$ and $\le$ the scene's `duration`.
- You can place multiple actions inside a single `at <time>s:` block; all actions inside that block start simultaneously at `<time>s`.
- Timeline blocks can appear in any order in the file (the compiler sorts them chronologically), though writing them in ascending time order is recommended.

---

### 4.6 Facial Expressions

Use `expression <name>` inside an `at <time>s:` block to switch the avatar's facial expression. Expressions persist until the next `expression` statement on the timeline.

| Expression Name | Eyes Layer Used | Mouth Layer Used | Best Used For |
| :--- | :--- | :--- | :--- |
| **`neutral`** | `eyes_open.svg` | `mouth_neutral.svg` | Default narration, calm listening |
| **`happy`** | `eyes_open.svg` | `mouth_happy.svg` | Laughing, hype moments, outro |
| **`sad`** | `eyes_open.svg` | `mouth_sad.svg` | Tragic backstory, disappointment |
| **`angry`** | `eyes_angry.svg` | `mouth_angry.svg` | Frustration, boss fight, rant |
| **`surprised`** | `eyes_open.svg` | `mouth_surprised.svg` | Sudden twist, plot reveal ("Wait, what?!") |
| **`shocked`** | `eyes_shocked.svg` | `mouth_shocked.svg` | Extreme disbelief, S-rank drop, cliffhanger |
| **`smirk`** | `eyes_open.svg` | `mouth_smirk.svg` | Cocky reaction, cheeky observation, irony |

*(Note: Automatic idle blinking temporarily overrides `eyes_open.svg` with `eyes_closed.svg` for 150ms, while preserving `eyes_shocked.svg` during extreme shock.)*

---

### 4.7 Animations & Transform Channels

AvatarScript supports **7 built-in animation primitives** divided into two categories:
1. **Persistent Property Channel Animations** (`move`, `scale`, `rotate`, `fade`) — smoothly interpolate an avatar's state to a new value and **stay** at that new value after the animation completes.
2. **Transient Procedural Animations** (`shake`, `bounce`, `nod`) — apply an energetic displacement curve over `duration` and automatically return cleanly to `0` offset when finished.

Both `animate <kind> ...` syntax and direct command shorthand are supported:

#### 1. `shake` (Transient Horizontal Shake)
Oscillates the avatar horizontally with a damped sine wave ($\sin(8\pi p) \cdot (1 - p)$) that decays to zero.
```ava
animate shake duration 0.4s
animate shake duration 0.5s intensity 20
```
- `duration <TIME>` *(required)*: How long the shake lasts.
- `intensity <NUMBER>` *(optional, default `15.0`)*: Maximum horizontal pixel amplitude.

#### 2. `bounce` (Transient Jump + Squash & Stretch)
Makes the avatar jump vertically along a two-hop arc ($-|\sin(2\pi p)|$) with subtle layer squash-and-stretch.
```ava
animate bounce duration 0.6s
animate bounce duration 0.5s intensity 25 easing ease_out
```
- `duration <TIME>` *(required)*: Total jump duration.
- `intensity <NUMBER>` *(optional, default `15.0`)*: Base jump height parameter.
- `easing <NAME>` *(optional, default `linear`)*: Easing curve applied to the bounce progression.

#### 3. `nod` (Transient Head Nod / Torso Pitch)
Applies an emphatic pitch rotation downward and back ($\sin(2\pi p)$) to emphasize agreements, explanations, or confident punctuation.
```ava
animate nod duration 0.4s intensity 12
nod duration 0.35s intensity 10
```
- `duration <TIME>` *(required)*: How long the nod lasts.
- `intensity <NUMBER>` *(optional, default `15.0`)*: Maximum angular tilt in degrees.

#### 4. `move` (Relative Offset or Absolute Position)
Moves the avatar smoothly across the canvas.
- **Relative Offset (`x:<dx> y:<dy>`)** — adds `(dx, dy)` pixels to the avatar's current position at the start of the move:
  ```ava
  move x:50 y:0 duration 0.4s easing ease_out
  move x:-80 y:20 duration 0.5s easing ease_in_out
  ```
- **Absolute Canvas Coordinates (`to_x:<x> to_y:<y>`)** — moves the avatar to an exact pixel coordinate on the canvas:
  ```ava
  move to_x:960 to_y:650 duration 0.6s easing ease_in_out
  ```
*(You can also write `animate move x:30 y:0 duration 0.3s`.)*

#### 4. `scale` (Zoom / Size Multiplier)
Interpolates the avatar's scale multiplier from its current scale to a new target scale (`> 0`).
```ava
scale 1.35 duration 0.4s easing ease_out
# Or keyword form:
animate scale to:1.0 duration 0.5s easing ease_in_out
```

#### 5. `rotate` (Tilt Angle in Degrees)
Interpolates the avatar's rotation angle in degrees (positive = clockwise, negative = counter-clockwise).
```ava
rotate -8 duration 0.3s easing ease_out
rotate 0 duration 0.3s easing ease_in_out
# Or keyword form:
animate rotate deg:12 duration 0.4s
```

#### 6. `fade` (Opacity `0.0` to `1.0`)
Fades the entire avatar rig in or out by interpolating its alpha opacity between `0.0` (invisible) and `1.0` (fully opaque).
```ava
# Fade out at the end of a video:
fade 0.0 duration 0.5s easing ease_in

# Fade back in:
fade 1.0 duration 0.4s easing ease_out
```

#### 7. `left_arm` and `right_arm` (Arm Rotations & Gestures)
Controls the rotation angle of each arm around its shoulder pivot socket (`(95, 265)` for the left shoulder, `(305, 265)` for the right shoulder) to create salutes, jutsu poses, pointing, raising hands, and battle stances:
```ava
# Raise right arm into a salute or pointing gesture (-55 degrees)
right_arm -55 duration 0.35s easing ease_out

# Raise left arm outward (45 degrees)
left_arm 45 duration 0.35s easing ease_out

# Reset arms back to resting pose
left_arm 0 duration 0.3s
right_arm 0 duration 0.3s
```
*(You can also use the general keyword form: `animate arm deg:-60 duration 0.4s`.)*

#### 8. `aura` (Dragon Ball Z Energy Highlighting System)
Adds a dynamic, customizable **Dragon Ball Z-inspired power-up aura** behind and around the character.

**Key Technical Guarantees:**
- **100% Non-Destructive**: The aura is generated as an independent procedural layer derived from the character's exact silhouette and alpha mask. The character's original pixels, colors, proportions, and outlines are **never modified or distorted**.
- **Dynamic Procedural Effects**: Features upward-surging multi-harmonic flame noise, a white-hot inner core, pulsating energy bloom, and violent electric lightning arcs (SSJ2 style).
- **Movement Synchronization**: The aura automatically tracks the character's translation, rotation, and scaling in real time.

```ava
# 1. Activate calm blue Ki aura
aura blue size:25 intensity:0.8 speed:1.2 sparks:0 duration 0.5s

# 2. Explosive Golden Super Saiyan power-up with electric sparks:
aura gold size:65 intensity:2.2 speed:2.5 sparks:1 duration 0.2s

# 3. Custom color presets (gold, blue, cyan, red, purple, green, white, orange, pink) or hex code:
aura #ff0055 size:40 intensity:1.5

# 4. Turn off aura cleanly:
aura none duration 0.3s
```

**Parameters for `aura`:**
- `color`: Named preset (`gold`, `yellow`, `blue`, `cyan`, `red`, `purple`, `violet`, `green`, `white`, `orange`, `pink`) or hex string (`#FF3300`).
- `size`: Bloom radius in pixels (default: `35.0`).
- `intensity`: Overall energy glow and flame brightness multiplier (default: `1.0`).
- `speed`: Animation frequency multiplier for upward energy surges (default: `1.0`).
- `sparks`: `1` (or `true`) to enable electric lightning arcs; `0` (or `false`) to disable.
- `duration`: Transition duration to interpolate intensity, size, and speed from current values.

#### 9. `hold` (Interactive Prop Rigging & Hand Sockets)
Equips and rigs vector props (microphones, swords, controllers, phones) to the character's left or right anatomical hand sockets (`(82, 330)` for left hand, `(318, 330)` for right hand). Props automatically track shoulder and arm rotations in real time:

- **Built-in Props**: `microphone`, `sword`, `controller`, `phone` (or release with `none` / `off`).
- **Scale Parameter (`scale:<multiplier>`)**: Custom scale multiplier (e.g. `scale:1.4`) to make items prominent and bold.
- **Initial Setup**: Can be declared directly inside the `avatar` definition:
  ```ava
  avatar "player":
      character "default"
      hold item:"microphone" hand:right scale:1.3
  ```
- **Timeline Swapping**: Can be dynamically attached, swapped, or sheathed at any timestamp:
  ```ava
  at 2.0s:
      hold item:"sword" hand:left scale:1.5
      hold item:"none" hand:right
  ```

#### 10. `talk` (Audio-Driven Viseme Lip-Sync)
Articulates speech mouths in real time synchronized either to an audio file (`.mp3`, `.wav`) or a procedural rhythm:

```ava
# 1. Real voiceover audio synchronization:
at 0.5s:
    talk audio:"production/voices/voice_part1.mp3" duration 6.5s threshold:0.12

# 2. Procedural rhythmic banter/chatter:
at 7.0s:
    talk duration 2.0s speed:1.2
```
- `audio:"<path>"`: Relative or absolute path to audio file. The engine analyzes 40ms RMS energy windows to swap between open visemes (`mouth_happy`, `mouth_surprised`) and closed resting mouth.
- `threshold:<num>`: RMS noise floor sensitivity (default `0.12`).
- `speed:<num>`: Frequency multiplier for procedural chatter.

---

### 4.8 2.5D VTuber Depth System (`head_turn` & `look`)

AvatarScript includes a complete **2.5D pseudo-3D parallax and gaze tracking engine**. It transforms flat 2D layered SVG avatars into expressive Live2D/VTuber-style characters with volumetric depth without requiring complex 3D meshes or external rigging software.

#### The Three Core Depth Principles:
1. **Differential Parallax Layer Shift**:
   When the head rotates, foreground layers shift faster than background layers across the focal axis:
   $$\Delta x_{\text{eyes}} > \Delta x_{\text{mouth}} > \Delta x_{\text{head}} > \Delta x_{\text{body}}$$
   - Head Base shifts subtly: $ny \cdot 6.0\text{px}$
   - Mouth shifts moderately: $ny \cdot 18.0\text{px}$
   - Eyes shift significantly: $ny \cdot 24.0\text{px}$
2. **Perspective Curvature Compression**:
   As the head turns sideways, the face wraps around a cylindrical skull volume. The eyes and mouth compress horizontally:
   $$\text{scale\_x} = 1.0 - 0.20 \cdot |ny|$$
3. **Independent Eye Pupil Gaze Tracking (`look`)**:
   Pupils can track left/right/up/down independently of head direction, enabling natural conversational eye contact and wandering gazes.

#### Syntax & Case Reference:

##### Case A: Basic Head Turn (`yaw` & `pitch`)
Turn the head horizontally (`yaw`) and vertically (`pitch`) with custom duration and easing:
```ava
at 1.0s:
    # Look slightly right (+28 deg) and down (+10 deg)
    head_turn yaw:28 pitch:10 duration 0.4s easing ease_out
```

##### Case B: Eye Gaze Direction Tracking (`look at:<direction>`)
Quickly dart the eyes towards standard focal points (`left`, `right`, `up`, `down`, `center`):
```ava
at 1.2s:
    look at:left duration 0.2s easing ease_out

at 2.0s:
    look at:right duration 0.2s easing ease_out

at 3.0s:
    look at:center duration 0.15s
```

##### Case C: Precise Pixel Look Coordinates (`look x:<dx> y:<dy>`)
For nuanced pupil targeting:
```ava
at 2.5s:
    look x:8.0 y:-4.0 duration 0.2s
```

##### Case D: Coordinated VTuber Conversation (Turn + Gaze + Viseme)
Combine head rotation, eye darting, expression changes, and speech articulation simultaneously:
```ava
at 0.5s:
    head_turn yaw:-30 pitch:5 duration 0.5s easing ease_out
    look at:left duration 0.25s
    expression surprised
    talk audio:"production/voices/voice_part1.mp3" duration 4.0s
```

##### Case E: Reset to Center Camera
Smoothly return the avatar's head and eyes to default camera position:
```ava
at 4.5s:
    head_turn yaw:0 pitch:0 duration 0.4s easing ease_in_out
    look at:center duration 0.25s
    expression happy
```

---

### 4.9 Easing Functions

Every animation accepts an optional `easing <name>` parameter (defaults to `linear` if omitted):

| Easing Name | Formula $f(t)$ for $t \in [0, 1]$ | Motion Feel |
| :--- | :--- | :--- |
| **`linear`** | $t$ | Constant mechanical speed from start to finish |
| **`ease_in`** | $t^2$ | Starts slow, accelerates into the target (great for `fade 0.0` exits) |
| **`ease_out`** | $t \cdot (2 - t)$ | Starts fast, decelerates smoothly into the resting pose (best for reaction punch-ins) |
| **`ease_in_out`** | $3t^2 - 2t^3$ (piecewise quadratic) | Smooth acceleration and deceleration (best for camera/avatar `move` transitions) |
| **`elastic_out`** | $2^{-10t} \cdot \sin((t - p/4)(2\pi/p)) + 1$ | Energetic spring bounce with overshoot (best for excited pop-ins and punchy zooms) |

---

### 4.10 Simultaneous & Overlapping Animations

AvatarScript's runtime engine evaluates each property channel independently:
1. **Different Properties Run Simultaneously**: You can combine `move`, `scale`, `rotate`, `fade`, `shake`, and `bounce` at the exact same timestamp (`at 3s:`) and they will blend seamlessly.
2. **Overlapping Same-Property Animations (Snapshot-on-Start)**: If a `move` from `0s` to `2s` is still in progress when another `move` begins at `1s`, the runtime snapshots the exact interpolated `(x, y)` coordinate at `t = 1.0s` and smoothly transitions from that point to the new target without any visual pop or jump.

---

## 5. Real-World Production Recipes

### Recipe 1: YouTube 16:9 Commentary Overlay
Render a transparent PNG sequence of your avatar positioned in the bottom-right corner so you can overlay it onto your 1920x1080 manhwa recap video:

```ava
scene "youtube_corner_overlay":
    canvas 1920x1080
    background "#000000"
    fps 30
    duration 8s

    avatar "commentator":
        character "default"
        position x:1620 y:760
        scale 0.95

        idle:
            breathe
            blink every 3.8s

        at 0s:
            expression neutral

        at 2.0s:
            expression surprised
            scale 1.08 duration 0.25s easing ease_out
            animate bounce duration 0.4s

        at 4.5s:
            expression shocked
            animate shake duration 0.4s intensity 14

        at 6.5s:
            expression happy
            scale 0.95 duration 0.35s easing ease_in_out
```
Export with transparency:
```powershell
& "avatarscript\.venv\Scripts\avatarscript.exe" export-frames youtube_corner_overlay.ava -o overlay_frames
```

---

### Recipe 2: Vertical 9:16 Manhwa Shorts Narrator (60 FPS)
See the included [manhwa_commentary_shorts.ava](file:///c:/Users/wergh/Desktop/sss%20class%20suici/avatarscript/examples/manhwa_commentary_shorts.ava) example for a complete `1080x1920` @ `60 FPS` vertical Shorts template that cycles through all 6 expressions and all 6 animations.

---

### Recipe 3: Multi-Avatar Co-Host Reaction Scene
You can place multiple `avatar` blocks inside a single `scene` to animate a duo podcast or two-host reaction:

```ava
scene "duo_reaction":
    canvas 1920x1080
    background "#181825"
    fps 30
    duration 6s

    avatar "left_host":
        character "default"
        position left
        scale 1.1

        idle:
            breathe
            blink every 4s

        at 0s:
            expression happy
        at 2.5s:
            expression shocked
            animate bounce duration 0.5s

    avatar "right_host":
        character "default"
        position right
        scale 1.1

        idle:
            breathe
            blink every 3.2s

        at 0s:
            expression neutral
        at 3.0s:
            expression angry
            animate shake duration 0.4s intensity 18

    render "duo_reaction.mp4"
```

---

### Recipe 4: Cinematic Flight & Dynamic Scale Control
Take full advantage of multi-channel coordination (`move`, `scale`, `rotate`, `aura`, and `head_turn`) to have an avatar take off, fly dynamically across the 1080p canvas, dive closer into camera (huge scale zoom), and swoop back out into the distance:

```ava
scene "Flying_Hero_Showcase":
    canvas 1920x1080
    background "#0d0f18"
    fps 30
    duration 7.0s
    render "renders/flying_showcase.mp4"

    avatar "hero":
        character "ninja"
        position x:960 y:850
        scale 0.95
        hold item:"sword" hand:right scale:1.4

        idle:
            breathe
            blink every 3.0s

        at 0.0s:
            expression neutral

        # 1. Takeoff: ignite energy aura, lift off, tilt forward into flight
        at 1.0s:
            expression angry
            aura cyan size:45 intensity:1.5 speed:1.8 sparks:1 duration 0.4s
            move to_x:960 to_y:450 duration 0.7s easing ease_out
            rotate -12 duration 0.5s easing ease_out
            scale 1.15 duration 0.7s easing ease_out
            head_turn yaw:15 pitch:-12 duration 0.4s
            look at:up duration 0.2s

        # 2. High-speed swoop toward camera: massive scale zoom (flying right at viewer)
        at 2.2s:
            expression shocked
            aura gold size:70 intensity:2.2 speed:2.5 sparks:1 duration 0.3s
            move to_x:1350 to_y:280 duration 0.8s easing ease_in_out
            scale 1.85 duration 0.8s easing ease_in_out
            rotate 15 duration 0.6s easing ease_in_out
            head_turn yaw:-25 pitch:10 duration 0.5s
            look at:left duration 0.2s
            right_arm -65 duration 0.3s

        # 3. Bank and fly across into the distance (shrink down to scale 0.55)
        at 3.5s:
            expression smirk
            aura blue size:30 intensity:1.0 speed:1.2 sparks:0 duration 0.5s
            move to_x:380 to_y:220 duration 1.2s easing ease_in_out
            scale 0.55 duration 1.2s easing ease_in_out
            rotate -20 duration 0.8s easing ease_in_out
            head_turn yaw:35 pitch:-15 duration 0.6s
            look at:right duration 0.3s
            right_arm 0 duration 0.4s

        # 4. Swoop back to center screen and hover steadily at standard scale
        at 5.2s:
            expression happy
            aura gold size:40 intensity:1.2 speed:1.0 sparks:1 duration 0.5s
            move to_x:960 to_y:540 duration 0.9s easing ease_out
            scale 1.20 duration 0.9s easing ease_out
            rotate 0 duration 0.6s easing ease_out
            head_turn yaw:0 pitch:0 duration 0.5s easing ease_in_out
            look at:center duration 0.3s
```

---

## 6. Built-in Characters & Creating Custom SVG Characters

### 6.1 Built-in Characters
AvatarScript includes **3 ready-to-use characters** inside `assets/characters/`:
- **`"default"`**: The classic blue hoodie avatar with interchangeable eyes and mouths.
- **`"ninja"`**: Dark shinobi gi, crimson sash obi belt, black stealth hood with face slit, and silver forehead headband plate.
- **`"demon"`**: Crimson skin, twin dark horn spires, forehead rune mark, dark purple horned armor with flame chest emblem, and clawed hands.

Example:
```ava
avatar "shinobi":
    character "ninja"

avatar "oni":
    character "demon"
```

### 6.2 Creating Custom SVG Characters
Characters live under [assets/characters/](file:///c:/Users/wergh/Desktop/sss%20class%20suici/avatarscript/assets/characters/). To create a new character named `"cyber_host"`, create a folder `assets/characters/cyber_host/` containing these **modular SVG files**, each using `viewBox="0 0 400 500"`:

| Layer Group | Z-Order | Required SVG Files |
| :--- | :--- | :--- |
| **Body** | `0` (Back) | `body.svg` |
| **Left Arm** | `1` | `left_arm.svg` (pivots around shoulder `(95, 265)`) |
| **Right Arm** | `2` | `right_arm.svg` (pivots around shoulder `(305, 265)`) |
| **Head** | `3` | `head.svg` |
| **Eyes** | `4` | `eyes_open.svg`, `eyes_closed.svg`, `eyes_angry.svg`, `eyes_shocked.svg` |
| **Mouth** | `5` (Front) | `mouth_neutral.svg`, `mouth_happy.svg`, `mouth_sad.svg`, `mouth_angry.svg`, `mouth_surprised.svg`, `mouth_shocked.svg`, `mouth_smirk.svg` |

Then reference your new character in any `.ava` script:
```ava
    avatar "host":
        character "cyber_host"
```

---

## 7. Compiler Diagnostics & Troubleshooting

Whenever a script contains a typo or invalid value, `avatarscript` prints the exact file, line number, column number, offending source line, and a caret (`^`) pointer.

**Example 1 — Unknown Expression:**
```text
[Validation Error] in broken.ava (1 error(s)):
  - Line 7, Col 13: Unknown expression 'super_saiyan' (allowed: ['angry', 'happy', 'neutral', 'sad', 'shocked', 'surprised'])
       7 |             expression super_saiyan
         |             ^
```

**Example 2 — Timestamp Exceeds Scene Duration:**
```text
[Validation Error] in broken.ava (1 error(s)):
  - Line 14, Col 9: Timeline timestamp 15.0s exceeds scene duration 12.0s
      14 |         at 15s:
         |         ^
```

**Example 3 — Undefined Character Folder:**
```text
[Validation Error] in broken.ava (1 error(s)):
  - Line 6, Col 9: Undefined character 'naruto' (directory not found in ...\assets\characters)
       6 |         character "naruto"
         |         ^
```

---

## 8. Formal Grammar Summary

For reference, the complete Lark `LALR(1)` grammar implemented in [grammar.lark](file:///c:/Users/wergh/Desktop/sss%20class%20suici/avatarscript/avatarscript/grammar.lark):

```ebnf
scene "<name>":
    canvas <WIDTH>x<HEIGHT>
    background "<HEX_COLOR>"
    fps <NUMBER>
    duration <TIME>

    avatar "<id>":
        character "<folder_name>"
        position (left | center | right | x:<NUM> y:<NUM>)
        scale <SIGNED_NUMBER>
        rotation <SIGNED_NUMBER>

        idle:
            breathe
            blink [every <TIME>]

        at <TIME>:
            expression (neutral | happy | sad | angry | surprised | shocked)
            animate <kind> [duration <TIME>] [easing <NAME>] [intensity <NUM>] [<key>:<NUM> ...]
            (move | scale | rotate | fade) [<NUM> | <key>:<NUM> ...] duration <TIME> [easing <NAME>]

    render "<output_path.mp4>"
```
