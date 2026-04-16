FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Install system dependencies (needed for psycopg2 and other C extensions)
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create a dedicated non-root runtime user.
RUN groupadd --system appuser \
    && useradd --system --gid appuser --create-home --home-dir /home/appuser --shell /usr/sbin/nologin appuser

# Copy application code
COPY --chown=appuser:appuser . .

# Expose port
EXPOSE 8000

USER appuser

# Start command
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
