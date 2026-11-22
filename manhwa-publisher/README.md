# Manhwa Publisher — Autonomous YouTube Publishing System

A standalone, production-ready Python CLI application that authenticates with YouTube Data API v3 via OAuth 2.0 and lets another AI video-production agent validate, upload, thumbnail, organize into playlists, and schedule long-form videos and YouTube Shorts with a single terminal command.

---

## 1. Installation on Windows

```powershell
git clone https://github.com/<your-username>/manhwa-publisher.git
cd manhwa-publisher
```

## 2. Python Environment Setup

Python **3.10+** is required.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# Optional: install editable package + dev tools
pip install -e ".[dev]"
```

> **Note:** On Windows, `tzdata` is included in `requirements.txt` so timezone names such as `Africa/Tunis` work reliably with Python's `zoneinfo`.

## 3. FFmpeg / FFprobe Installation

`manhwa-publisher` uses `ffprobe` to inspect video streams, codecs, resolution, aspect ratio, duration, and file integrity.

Install FFmpeg on Windows using Winget:

```powershell
winget install Gyan.FFmpeg
```

Restart your terminal and verify:

```powershell
ffprobe -version
```

## 4. Google Cloud Project Creation

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Click **Select a project** → **New Project**.
3. Name it `manhwa-publisher` and click **Create**.

## 5. YouTube Data API v3 Activation

1. In your new Google Cloud project, open **APIs & Services** → **Library**.
2. Search for **YouTube Data API v3**.
3. Click **Enable**.

## 6. OAuth 2.0 Credential Configuration

1. Go to **APIs & Services** → **OAuth consent screen**.
   - Choose **External** (or Internal if using Google Workspace).
   - Fill in App name (`Manhwa Publisher`), User support email, and Developer contact email.
   - Add Scopes:
     - `https://www.googleapis.com/auth/youtube.upload`
     - `https://www.googleapis.com/auth/youtube`
     - `https://www.googleapis.com/auth/youtube.readonly`
   - Under **Test users**, add the Google account that owns your YouTube channel.
2. Go to **APIs & Services** → **Credentials** → **Create Credentials** → **OAuth client ID**.
   - Application type: **Desktop app**.
   - Name: `Manhwa Publisher Desktop`.
3. Download the JSON file and save it as:
   ```text
   credentials/client_secrets.json
   ```

## 7. First-Time Authentication

Run the interactive OAuth flow once:

```powershell
python -m publisher auth
```

Approve access in your browser. Your refreshable token is saved to `credentials/token.json`.

Verify everything (FFprobe, SQLite DB, OAuth token, YouTube channel):

```powershell
python -m publisher doctor
```

## 8. Publishing a Video

```powershell
python -m publisher publish `
  --video ".\output\sss-chapter-07.mp4" `
  --metadata ".\examples\long_video.json" `
  --approve
```

Upload privately (no approval flag needed):

```powershell
python -m publisher publish `
  --video ".\output\sss-chapter-07.mp4" `
  --metadata ".\examples\private_video.json" `
  --visibility private
```

Publish immediately:

```powershell
python -m publisher publish `
  --video ".\output\sss-chapter-07.mp4" `
  --metadata ".\examples\long_video.json" `
  --now `
  --approve
```

Wait for YouTube processing to finish before exiting:

```powershell
python -m publisher publish `
  --video ".\output\sss-chapter-07.mp4" `
  --metadata ".\examples\long_video.json" `
  --visibility private `
  --wait-processing
```

## 9. Publishing Shorts (and Linking to a Long Video)

Set `"type": "short"` in your metadata JSON (see `examples/short_video.json`):

```powershell
python -m publisher publish `
  --video ".\output\sss-chapter-07-short.mp4" `
  --metadata ".\examples\short_video.json" `
  --related-job-id 15 `
  --approve
```

- Pass `--related-job-id <LONG_JOB_ID>` (or `--related-video-id <YOUTUBE_ID>`, or set `related_video_id` / `related_job_id` in the JSON).
- `manhwa-publisher` automatically resolves the long video's YouTube URL, appends `Watch the full video: https://www.youtube.com/watch?v=...` to the Short's description, stores the link in SQLite, and returns `studio_edit_url` so you can set YouTube Studio's native Shorts **Related video** button in 2 clicks (YouTube Data API v3 does not expose that Studio-only button).

`manhwa-publisher` inspects dimensions and duration and logs warnings if a Short is landscape or over 3 minutes, while letting YouTube make the final Shorts classification.

## 10. Scheduling

Include a timezone-aware ISO-8601 `publish_at` timestamp in your metadata JSON:

```json
{
  "title": "SSS-Class Suicide Hunter - Chapter 7",
  "type": "long",
  "visibility": "private",
  "publish_at": "2026-11-25T20:00:00+01:00"
}
```

- `manhwa-publisher` automatically converts `publish_at` to RFC 3339 UTC and sets `privacyStatus: "private"` as required by YouTube Data API v3.
- If `safety.require_approval` is `true` in `config.yaml`, pass `--approve` to allow scheduled or public publication.

## 11. Playlist Configuration

Add `"playlist_id": "PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"` to your metadata JSON. Playlist insertion is tracked independently in SQLite—if it fails after the video is uploaded, `python -m publisher retry <JOB_ID>` will only retry the playlist insertion without re-uploading the video.

## 12. Troubleshooting

| Symptom | Fix |
|---|---|
| `ffprobe executable not found` | Install FFmpeg (`winget install Gyan.FFmpeg`) and restart terminal. |
| Exit code `3` (Auth failure) | Run `python -m publisher auth` to refresh or re-authorize `credentials/token.json`. |
| Exit code `5` (Duplicate video) | The exact video SHA-256 was already uploaded. Check `python -m publisher status`. |
| Exit code `6` (Requires approval) | Pass `--approve` or upload with `--visibility private`, or set `safety.require_approval: false` in `config.yaml`. |
| Job status `needs_attention` | An uncertain network timeout occurred during `videos.insert`. Check YouTube Studio first so you never create duplicate uploads. |
| Thumbnail or playlist failed | Run `python -m publisher retry <JOB_ID>` — the video will NOT be re-uploaded. |

### Other Useful Commands

```powershell
python -m publisher validate --video ".\output\video.mp4" --metadata ".\examples\long_video.json"
python -m publisher status
python -m publisher status --video-id YOUTUBE_VIDEO_ID --remote
python -m publisher queue
python -m publisher retry 1
```

## 13. AI-Agent Integration

Another AI video-production agent only needs to produce:
1. A finished `.mp4` video
2. An optional thumbnail image (`.jpg` / `.png`, ≤ 2 MB)
3. A metadata `.json` file

Then invoke:

```powershell
python -m publisher publish `
  --video "output/final-video.mp4" `
  --metadata "output/final-video.json" `
  --json
```

In `--json` mode:
- **stdout** contains **exactly one JSON object**.
- **stderr** receives all progress logs.

Example JSON response:

```json
{
  "success": true,
  "job_id": 15,
  "video_id": "YOUTUBE_VIDEO_ID",
  "url": "https://www.youtube.com/watch?v=YOUTUBE_VIDEO_ID",
  "status": "scheduled",
  "message": "Video uploaded and scheduled successfully for 2026-11-25T19:00:00Z."
}
```

### Exit Codes

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | General failure |
| `2` | Invalid arguments, metadata, or video validation failure |
| `3` | Authentication failure |
| `4` | Upload or post-upload operation failure |
| `5` | Duplicate video detected (SHA-256 match) |
| `6` | Blocked by safety policy (manual approval required) |

## 14. Security and Backups

- **Never commit secrets**: `credentials/*.json` and `.env` are excluded in `.gitignore`.
- **Log redaction**: OAuth tokens, refresh tokens, and bearer headers are automatically redacted from console and `logs/publisher.jsonl`.
- **Database backups**: Back up `data/publisher.db` periodically to preserve upload history and duplicate-prevention hashes.

## Running Tests

```powershell
python -m unittest discover -s tests -v
```
