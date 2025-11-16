# Debian Slim - Best for aiortc
FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Install dependencies required by aiortc & av
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    ffmpeg \
    libavformat-dev \
    libavcodec-dev \
    libavdevice-dev \
    libavutil-dev \
    libswscale-dev \
    libswresample-dev \
    libv4l-dev \
    libopus-dev \
    libvpx-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire app
COPY . .

EXPOSE 8080

CMD ["python", "python_service.py"]