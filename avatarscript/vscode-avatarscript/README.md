# AvatarScript (`.ava`) — VS Code / Antigravity IDE Extension

<p align="center">
  <img src="icons/avatarscript-logo.png" width="128" height="128" alt="AvatarScript Logo"/>
</p>

Run, preview, and export `.ava` reaction avatar scripts directly inside VS Code / Antigravity **with one click (no terminal required)**, complete with syntax highlighting, `.ava` file icons, live error squiggles, and snippets.

---

## 1. Running `.ava` Scripts Without the Command Line

Whenever you open any `.ava` file (such as `anime_reaction.ava`), you have **5 ways** to run it directly from the editor UI:

### A. Top-Right Editor Toolbar Buttons (Recommended)
In the top-right corner of the editor tab bar:
- Click **`▶` (AvatarScript: Live Preview)** — Immediately opens the real-time Pygame preview window (`SPACE` to play/pause, `R` to restart, `LEFT`/`RIGHT` to scrub).
- Click **`🎥` (AvatarScript: Render to MP4 Video)** — Renders your `.ava` script directly to an H.264 `.mp4` video with a live progress notification in the bottom-right corner.

### B. Bottom Status Bar Buttons
When an `.ava` file is active, two clickable buttons appear in the bottom-left Status Bar:
- **`▶ Preview .ava`** — Launches the interactive preview window.
- **`🎥 Render MP4`** — Exports the MP4 video.

### C. Right-Click Context Menu (Editor or File Explorer)
Right-click anywhere inside an `.ava` file (or right-click any `.ava` file in the left Explorer sidebar) and choose:
1. **`AvatarScript: Live Preview (.ava)`**
2. **`AvatarScript: Render to MP4 Video`**
3. **`AvatarScript: Export Transparent PNG Frames`** (automatically exports 32-bit RGBA PNGs into `<script_name>_frames/`)
4. **`AvatarScript: Validate Script`**

### D. Keyboard Shortcuts
While editing an `.ava` file:
- **`Ctrl+Alt+P`** (`Cmd+Alt+P` on Mac) → **Live Preview**
- **`Ctrl+Alt+R`** (`Cmd+Alt+R` on Mac) → **Render to MP4 Video**

### E. Live Error Checking on Save (`Ctrl+S`)
Every time you save (`Ctrl+S`) an `.ava` file, the extension automatically runs the AvatarScript compiler in the background:
- If there is a syntax or semantic error, **red squiggly lines** appear directly under the exact line and column in your editor and inside the **Problems** tab.

---

## 2. Syntax Highlighting Color Palette

- **Block Headers** (`scene`, `avatar`, `idle:`, `at 3.5s:`) — **Bold Purple** (`#C792EA`)
- **Scene & Rig Properties** (`canvas`, `background`, `fps`, `duration`, `character`, `position`, `rotation`, `render`) — **Soft Blue** (`#82AAFF`)
- **Animations & Transforms** (`animate`, `shake`, `bounce`, `move`, `scale`, `rotate`, `fade`) — **Bold Cyan** (`#89DDFF`)
- **Facial Expressions** (`neutral`, `happy`, `sad`, `angry`, `surprised`, `shocked`) — **Italic Gold** (`#FFCB6B`)
- **Easing Curves** (`linear`, `ease_in`, `ease_out`, `ease_in_out`) — **Mint Green** (`#C3E88D`)
- **Time & Resolution Literals** (`0.4s`, `12s`, `1920x1080`, `1080x1920`) — **Coral Orange** (`#F78C6C`) & **Rose Red** (`#FF5370`)

---

## 3. How to Install / Update the Extension

Run this single command once (or use `Ctrl+Shift+P` → **`Extensions: Install from VSIX...`** and select `vscode-avatarscript-0.1.0.vsix`):

```powershell
& "c:\Users\wergh\Desktop\sss class suici\avatarscript\.venv\Scripts\avatarscript.exe" install-extension
```
Then press `Ctrl+Shift+P` → **`Developer: Reload Window`**.
