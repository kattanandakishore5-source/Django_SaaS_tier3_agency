FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root system user and required directories
RUN addgroup --gid 1000 django_user && \
    adduser --disabled-password --gecos "" --uid 1000 --ingroup django_user django_user && \
    mkdir -p /app/staticfiles /app/media && \
    chown -R django_user:django_user /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files and transfer ownership
COPY . .
RUN chmod +x /app/entrypoint.sh && \
    chown -R django_user:django_user /app

USER django_user

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
