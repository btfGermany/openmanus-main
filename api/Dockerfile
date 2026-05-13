# OpenManus API Service Dockerfile

FROM python:3.11-slim

# Set environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt api/requirements.txt
RUN pip install --no-cache-dir -r api/requirements.txt

# Copy the rest of the application
COPY . /app/

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "-m", "api.main"]