# Video Downloader

FastAPI + yt-dlp backend with a single-page frontend.

## Run

```bash
# ffmpeg is required (merges video+audio, converts to MP3)
# macOS: brew install ffmpeg   Ubuntu: sudo apt install ffmpeg

python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Open http://localhost:8000

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/info` `{url}` | Title, thumbnail, duration, available qualities |
| POST | `/api/download` `{url, quality}` | Starts a job, returns `job_id` |
| GET | `/api/progress/{job_id}` | `status`, `progress`, `speed`, `error` |
| GET | `/api/file/{job_id}` | Streams the file, then deletes it from the server |

`quality`: `best`, `1080`, `720`, `480`, `audio`

## Notes

- Jobs live in memory, so they are lost on restart. For production, move to Redis + a worker (RQ/Celery).
- Keep yt-dlp updated (`pip install -U yt-dlp`); most breakages are fixed upstream within days.
- Use it for personal use or content you have rights to. YouTube's ToS restrict downloading.
# yt-downloader
