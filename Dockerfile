# Use the latest official Python image (Debian-based)
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive

# Create and set working directory
WORKDIR /app

# Install system dependencies (optional: add git or curl if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt first (to leverage Docker cache)
COPY requirements.txt .

# Install Python dependencies safely
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the rest of the app
COPY . .

# Expose port if your app uses one (example: 8000)
EXPOSE 8000

# Default command to run your bot/app
CMD ["python", "main.py"]
