# Base
FROM python:3.11-slim

# System deps for yt-dlp + networking
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg curl ca-certificates jq coreutils git bash \
 && rm -rf /var/lib/apt/lists/*

# Workdir
WORKDIR /app

# Clone official yt-dlp and install it
RUN git clone https://github.com/yt-dlp/yt-dlp.git /opt/yt-dlp \
 && pip install --no-cache-dir /opt/yt-dlp

# Python deps for the wrapper
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY app.py /app/

# Railway will inject $PORT; FastAPI binds to it
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
EXPOSE 8080

CMD ["uvicorn", "app:api", "--host", "0.0.0.0", "--port", "8080"]
