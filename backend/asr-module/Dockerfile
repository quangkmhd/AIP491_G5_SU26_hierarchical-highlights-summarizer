FROM python:3.10-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1 \
  DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install system dependencies for audio decoding & C++ runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
  ffmpeg \
  libsndfile1 \
  curl \
  && rm -rf /var/lib/apt/lists/*

# Copy requirements and install python dependencies
COPY asr-module-requirements.txt .
RUN pip install --no-cache-dir -r asr-module-requirements.txt

# Copy application source code and models
COPY . .

# Expose HTTP port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/readyz || exit 1

# Start Uvicorn server
CMD ["python", "main.py"]
