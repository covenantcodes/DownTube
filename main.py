import os
import shutil
import tempfile
import threading
import uuid
from pathlib import Path

import yt_dlp
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.background import BackgroundTask

app = FastAPI(title="DownTube")

COOKIES_FROM_BROWSER = os.environ.get("YTDLP_COOKIES_FROM_BROWSER")

# yt-dlp rewrites the cookies file after each run to persist refreshed session
# cookies, so a read-only mount (e.g. Render Secret Files) has to be copied to
# a writable path first.
COOKIES_FILE = os.environ.get("YTDLP_COOKIES_FILE")
if COOKIES_FILE:
    if os.path.exists(COOKIES_FILE):
        writable_cookies_file = Path(tempfile.gettempdir()) / "ytdlp_cookies.txt"
        shutil.copyfile(COOKIES_FILE, writable_cookies_file)
        COOKIES_FILE = str(writable_cookies_file)
    else:
        print(f"WARNING: YTDLP_COOKIES_FILE={COOKIES_FILE!r} does not exist, ignoring")
        COOKIES_FILE = None


def cookie_opts() -> dict:
    """yt-dlp options that authenticate as a real browser.

    YouTube blocks datacenter IPs (Render, Railway, etc.) with
    "Sign in to confirm you're not a bot" unless requests carry cookies
    from a logged-in session.
    """
    if COOKIES_FILE:
        return {"cookiefile": COOKIES_FILE}
    if COOKIES_FROM_BROWSER:
        browser, _, profile = COOKIES_FROM_BROWSER.partition(":")
        return {"cookiesfrombrowser": (browser, profile or None, None, None)}
    return {}

JOBS: dict[str, dict] = {}
QUALITIES = {
    "best": "bv*+ba/b",
    "1080": "bv*[height<=1080]+ba/b[height<=1080]",
    "720": "bv*[height<=720]+ba/b[height<=720]",
    "480": "bv*[height<=480]+ba/b[height<=480]",
    "audio": "bestaudio/best",
}


class InfoRequest(BaseModel):
    url: str


class DownloadRequest(BaseModel):
    url: str
    quality: str = "best"


@app.post("/api/info")
def info(req: InfoRequest):
    try:
        with yt_dlp.YoutubeDL({"quiet": True, "noplaylist": True, **cookie_opts()}) as ydl:
            data = ydl.extract_info(req.url, download=False)
    except yt_dlp.utils.DownloadError as e:
        raise HTTPException(400, str(e).removeprefix("ERROR: "))
    except Exception as e:
        raise HTTPException(500, f"{type(e).__name__}: {e}")
    heights = sorted({f["height"] for f in data.get("formats", []) if f.get("height")}, reverse=True)
    return {
        "title": data.get("title"),
        "thumbnail": data.get("thumbnail"),
        "duration": data.get("duration"),
        "channel": data.get("uploader"),
        "qualities": ["best"] + [q for q in ("1080", "720", "480") if any(h >= int(q) for h in heights)] + ["audio"],
    }


def _run_job(job_id: str, url: str, quality: str):
    job = JOBS[job_id]
    workdir = Path(tempfile.mkdtemp(prefix="ytdl-"))
    job["dir"] = workdir

    def hook(d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            if total:
                job["progress"] = round(d["downloaded_bytes"] / total * 100, 1)
            job["speed"] = d.get("_speed_str", "").strip()
        elif d["status"] == "finished":
            job["status"] = "processing"

    opts = {
        "format": QUALITIES[quality],
        "outtmpl": str(workdir / "%(title).150B.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "progress_hooks": [hook],
        **cookie_opts(),
    }
    if quality == "audio":
        opts["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}]
    else:
        opts["merge_output_format"] = "mp4"

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
        job["file"] = next(workdir.iterdir())
        job["status"], job["progress"] = "done", 100
    except Exception as e:
        job["status"], job["error"] = "error", str(e).removeprefix("ERROR: ")
        shutil.rmtree(workdir, ignore_errors=True)


@app.post("/api/download")
def download(req: DownloadRequest):
    if req.quality not in QUALITIES:
        raise HTTPException(400, "Invalid quality")
    job_id = uuid.uuid4().hex
    JOBS[job_id] = {"status": "downloading", "progress": 0, "speed": ""}
    threading.Thread(target=_run_job, args=(job_id, req.url, req.quality), daemon=True).start()
    return {"job_id": job_id}


@app.get("/api/progress/{job_id}")
def progress(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return {k: job.get(k) for k in ("status", "progress", "speed", "error")}


@app.get("/api/file/{job_id}")
def file(job_id: str):
    job = JOBS.get(job_id)
    if not job or job.get("status") != "done":
        raise HTTPException(404, "File not ready")

    def cleanup():
        shutil.rmtree(job["dir"], ignore_errors=True)
        JOBS.pop(job_id, None)

    return FileResponse(job["file"], filename=job["file"].name, background=BackgroundTask(cleanup))


app.mount("/", StaticFiles(directory=Path(__file__).parent / "static", html=True), name="static")
