FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    unzip \
    tini \
    && rm -rf /var/lib/apt/lists/*

# Install yt-dlp
RUN pip install --no-cache-dir yt-dlp

# Create non-root user
RUN useradd --create-home --shell /bin/bash --user-group --uid 1000 appuser

# Create directories
RUN mkdir -p /var/log/app && chown -R appuser:appuser /var/log/app
RUN mkdir -p /app && chown -R appuser:appuser /app
RUN mkdir -p /tmp/railway-downloads && chown -R appuser:appuser /tmp/railway-downloads

# Set work directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8080/api/v1/health || exit 1

# Use tini as entrypoint
ENTRYPOINT ["tini", "--"]

# Default command - use uvicorn to run FastAPI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
