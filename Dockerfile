# Use official Python 3.11 slim image for a lightweight base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
# Prevent Python from writing pyc files to disc
ENV PYTHONDONTWRITEBYTECODE 1
# Prevent Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED 1

# Install system dependencies necessary for Python packages and Video processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    ffmpeg \
    imagemagick \
    ghostscript \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Imagemagick has a security policy that blocks some text rendering by default. 
# We remove the policy file to allow moviepy's TextClip to work.
RUN sed -i '/<policy domain="path" rights="none" pattern="@\*"/d' /etc/ImageMagick-6/policy.xml || true

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose the application port
EXPOSE 8000

# Run DB migrations then start the server.
# ${PORT:-8000} uses Render's injected $PORT in production, falls back to 8000 locally.
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
