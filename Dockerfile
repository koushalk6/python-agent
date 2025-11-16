FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PORT=8080

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY . /app
EXPOSE 8080
CMD ["python", "python_service.py"]










# FROM python:3.11-slim

# ENV PYTHONUNBUFFERED=1
# ENV PORT=8080

# # Minimal system packages
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     build-essential \
#     libssl-dev \
#     && rm -rf /var/lib/apt/lists/*

# WORKDIR /app

# # Copy requirements first for cache
# COPY requirements.txt /app/requirements.txt
# RUN pip install --upgrade pip
# RUN pip install --no-cache-dir -r /app/requirements.txt

# # Copy app
# COPY . /app

# EXPOSE 8080

# CMD ["python", "python_service.py"]
