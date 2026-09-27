FROM denoland/deno:bin-2.9.4 AS deno

FROM python:3.12-slim

# yt-dlp needs a JS runtime to solve YouTube's signature/PO-token challenges,
# without one every extraction fails with "Failed to extract any player response".
COPY --from=deno /deno /usr/local/bin/deno

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

CMD ["sh", "-c", "pip install --no-cache-dir -q -U yt-dlp; uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
