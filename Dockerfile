# Base
FROM python:3.11-slim

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg curl ca-certificates jq coreutils git bash \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install yt-dlp from the official GitHub repo
RUN git clone https://github.com/yt-dlp/yt-dlp.git /opt/yt-dlp \
 && pip install --no-cache-dir /opt/yt-dlp

# App deps
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# App
COPY app.py /app/

ENV PYTHONUNBUFFERED=1
ENV PORT=8080
EXPOSE 8080

CMD ["uvicorn", "app:api", "--host", "0.0.0.0", "--port", "8080"]
CMD ["uvicorn", "app:api", "--host", "0.0.0.0", "--port", "8080"]
