FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    ffmpeg \
    libavdevice-dev \
    libavfilter-dev \
    libavformat-dev \
    libavcodec-dev \
    libswscale-dev \
    libswresample-dev \
    libavutil-dev \
    && rm -rf /var/lib/apt/lists/*

# PYAV
RUN pip install av==10.0.0

# AIORTC with media support
RUN pip install aiortc==1.7.0








# FROM python:3.11-slim

# RUN apt-get update && apt-get install -y \
#     ffmpeg \
#     libavformat-dev libavcodec-dev libavutil-dev libavdevice-dev \
#     libavfilter-dev libswscale-dev \
#     libopus-dev libvpx-dev \
#     libssl-dev libffi-dev \
#     && rm -rf /var/lib/apt/lists/*

# WORKDIR /app

# COPY python_service.py .
# COPY requirements.txt .

# RUN pip install --no-cache-dir -r requirements.txt

# ENV PORT=8080
# EXPOSE 8080

# CMD ["python", "python_service.py"]






# # FROM python:3.11-slim

# # # Install system dependencies for aiortc
# # RUN apt-get update && apt-get install -y \
# #     ffmpeg \
# #     libavformat-dev libavcodec-dev libavutil-dev libavdevice-dev \
# #     libavfilter-dev libswscale-dev \
# #     libopus-dev libvpx-dev \
# #     libssl-dev libffi-dev \
# #     && rm -rf /var/lib/apt/lists/*

# # WORKDIR /app

# # COPY python_service.py .
# # COPY requirements.txt .

# # RUN pip install --no-cache-dir -r requirements.txt

# # ENV PORT=8080
# # EXPOSE 8080

# # CMD ["python", "python_service.py"]












# # # FROM python:3.11-slim

# # # ENV PYTHONUNBUFFERED=1
# # # ENV PORT=8080

# # # RUN apt-get update && apt-get install -y --no-install-recommends \
# # #     build-essential \
# # #     libssl-dev \
# # #     && rm -rf /var/lib/apt/lists/*

# # # WORKDIR /app
# # # COPY requirements.txt /app/requirements.txt
# # # RUN pip install --upgrade pip
# # # RUN pip install --no-cache-dir -r /app/requirements.txt
# # # COPY . /app
# # # EXPOSE 8080
# # # CMD ["python", "python_service.py"]










# # # # FROM python:3.11-slim

# # # # ENV PYTHONUNBUFFERED=1
# # # # ENV PORT=8080

# # # # # Minimal system packages
# # # # RUN apt-get update && apt-get install -y --no-install-recommends \
# # # #     build-essential \
# # # #     libssl-dev \
# # # #     && rm -rf /var/lib/apt/lists/*

# # # # WORKDIR /app

# # # # # Copy requirements first for cache
# # # # COPY requirements.txt /app/requirements.txt
# # # # RUN pip install --upgrade pip
# # # # RUN pip install --no-cache-dir -r /app/requirements.txt

# # # # # Copy app
# # # # COPY . /app

# # # # EXPOSE 8080

# # # # CMD ["python", "python_service.py"]
