
# Use Debian slim (stable for building aiortc)
FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Install system libs required by aiortc / av and build tools
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

# Copy requirements first for caching
COPY requirements.txt /app/requirements.txt

# Install python deps
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy app
COPY . /app

# Expose Cloud Run port
EXPOSE 8080

# Run the python service (aiohttp web.run_app will bind to $PORT)
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
