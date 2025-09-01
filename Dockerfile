FROM python:3.11-slim

# System deps: ffmpeg for yt-dlp merging; curl not required (we pip-install yt-dlp)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg ca-certificates \
  && rm -rf /var/lib/apt/lists/*

# Workdir
WORKDIR /app

# Copy and install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App
COPY app.py .

# Create writable data dir (Railway volume can mount here)
RUN mkdir -p /data

# Health stuff
ENV PORT=8000
EXPOSE 8000

# Start
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
