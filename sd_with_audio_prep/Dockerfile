# Use Python 3.12 (Compatible with pyproject.toml)
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system libraries for audio processing (libsndfile for soundfile, ffmpeg for librosa)
RUN apt-get update && apt-get install -y \
    libsndfile1 \
    ffmpeg \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Note: The weights/ directory may be ignored by .dockerignore or .gitignore.
# When running in a real environment, you should mount the weights directory via Volume:
# docker run -v /path/to/local/weights:/app/weights my-diarization-app

# Default run command (Can be modified depending on usage in external repo)
# CMD ["python", "tests/e2e_voxconverse_runner.py"]
