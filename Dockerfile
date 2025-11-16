# Use Debian slim for compatibility
FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Install system libraries needed by aiortc + av
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
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install python dependencies separately for caching
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . /app

EXPOSE 8080

CMD ["python", "python_service.py"]