# DownTube

A small self-hosted web app for downloading YouTube videos (or audio) at a chosen quality. FastAPI + [yt-dlp](https://github.com/yt-dlp/yt-dlp) backend, single-page vanilla JS frontend, no database required.

![status](https://img.shields.io/badge/status-active-brightgreen)
![license](https://img.shields.io/badge/license-MIT-blue)

## Features

- Paste a link, preview title/thumbnail/duration, pick a quality
- Choose best, 1080p, 720p, 480p, or audio-only (MP3)
- Live progress bar with download speed
- No accounts, no database — jobs are tracked in memory and files are deleted after they're served

## Prerequisites

- Python 3.10+
- [ffmpeg](https://ffmpeg.org/) (merges video+audio streams and converts to MP3)
  - macOS: `brew install ffmpeg`
  - Ubuntu/Debian: `sudo apt install ffmpeg`
  - Windows: [download a build](https://ffmpeg.org/download.html) and add it to `PATH`

## Quick start

```bash
git clone https://github.com/<your-username>/downtube.git
cd downtube

python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

pip install -r requirements.txt
uvicorn main:app --reload
```

Open http://localhost:8000

## Run with Docker

```bash
docker build -t downtube .
docker run -p 8000:8000 downtube
```

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/info` `{url}` | Title, thumbnail, duration, available qualities |
| POST | `/api/download` `{url, quality}` | Starts a job, returns `job_id` |
| GET | `/api/progress/{job_id}` | `status`, `progress`, `speed`, `error` |
| GET | `/api/file/{job_id}` | Streams the file, then deletes it from the server |

`quality`: `best`, `1080`, `720`, `480`, `audio`

## "Sign in to confirm you're not a bot"

YouTube blocks requests from datacenter IPs (Render, Railway, most cloud hosts) unless they carry cookies from a real, logged-in browser session. If `/api/info` or `/api/download` fails with this error, set one of these env vars:

- **`YTDLP_COOKIES_FILE`** — path to a `cookies.txt` (Netscape format) exported from a logged-in YouTube session in your browser, using an extension like [Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc). On Render, upload it as a **Secret File** (e.g. at `/etc/secrets/cookies.txt`) and point the env var at that path. Use a throwaway/alt Google account, not your main one — the cookies grant download access as that account and can expire or get flagged.
- **`YTDLP_COOKIES_FROM_BROWSER`** — for local dev only (there's no installed browser in a container): set it to a browser name like `chrome`, `firefox`, or `chrome:ProfileName` to pull cookies straight from your local browser profile.

Neither is set by default, so the app works cookie-free until you hit this error.

## Deploying publicly

If you host this for others to use, put it behind authentication (it's an open download proxy otherwise) and expect to keep `yt-dlp` updated, since YouTube changes frequently break extraction. A Dockerfile is included for deploying to any container platform (Render, Railway, Fly.io, a VPS, etc.).

## Known limitations

- Jobs live in memory, so they're lost on restart and won't work across multiple instances. For production use at scale, move job state to Redis and downloads to a worker queue (RQ/Celery).
- Single-instance only for the same reason.

## Contributing

Issues and PRs are welcome. Please:

- Keep changes focused and small
- Test locally (`uvicorn main:app --reload`) before submitting
- Note any new dependencies in `requirements.txt`

## Legal

This tool is intended for personal use or content you have the rights to download. YouTube's Terms of Service restrict downloading video content, and enforcement of that restriction is the responsibility of whoever deploys or uses this tool. The maintainers are not responsible for misuse.

## License

[MIT](LICENSE)
