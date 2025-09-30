# Use official Python slim image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    APP_HOME=/app \
    PORT=8000 \
    DATABASE_URL=postgresql://<username>:<password>@<host>:5432/<database>

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user and app directory
RUN useradd -m appuser
RUN mkdir -p $APP_HOME
RUN chown -R appuser:appuser $APP_HOME

# Set working directory
WORKDIR $APP_HOME

# Copy requirements and install as root (to make uvicorn globally available)
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Switch to non-root user
USER appuser

# Copy the rest of the backend code
COPY . $APP_HOME

# Expose FastAPI port
EXPOSE $PORT

# Default command to run Uvicorn
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
