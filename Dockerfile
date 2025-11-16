
# -----------------------------
# Base Image
# -----------------------------
FROM python:3.10-slim

# Avoid Python buffering
ENV PYTHONUNBUFFERED=1

# Install system dependencies needed by aiortc
RUN apt-get update && apt-get install -y \
    libavdevice-dev \
    libavfilter-dev \
    libavformat-dev \
    libavcodec-dev \
    libavutil-dev \
    libswscale-dev \
    libswresample-dev \
    libv4l-dev \
    libopus-dev \
    libvpx-dev \
    && rm -rf /var/lib/apt/lists/*

# -----------------------------
# App Directory
# -----------------------------
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY python_service.py .

# Cloud Run will set PORT automatically
ENV PORT=8080

EXPOSE 8080

# Run app
CMD ["python", "python_service.py"]





# FROM python:3.11-slim

# RUN apt-get update && apt-get install -y \
#     ffmpeg \
#     libavdevice-dev \
#     libavfilter-dev \
#     libavformat-dev \
#     libavcodec-extra \
#     libopus-dev \
#     libvpx-dev \
#     && apt-get clean

# WORKDIR /app

# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# COPY python_service.py .

# ENV PORT=8030

# CMD ["python", "python_service.py"]



# # FROM python:3.10-slim

# # RUN apt-get update && apt-get install -y \
# #     ffmpeg libavcodec-extra libavdevice-dev libavfilter-dev libavformat-dev \
# #     libavutil-dev libswresample-dev libswscale-dev && \
# #     apt-get clean

# # WORKDIR /app

# # COPY requirements.txt .
# # RUN pip install --no-cache-dir -r requirements.txt

# # COPY python_service.py .

# # CMD ["python", "python_service.py"]
