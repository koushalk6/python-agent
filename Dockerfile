# Lightweight Python image
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Install minimal system tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first (for caching)
COPY requirements.txt /app/requirements.txt

# Install python dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy app source
COPY . /app

# Expose port for Cloud Run
EXPOSE 8080

# Start service
CMD ["python", "python_service.py"]