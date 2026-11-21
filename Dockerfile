ARG NODE_BUILD_IMAGE=node:22-alpine
FROM ${NODE_BUILD_IMAGE} AS frontend_build
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --include=dev --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Asia/Shanghai \
    PYTHONPATH=/app

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    netcat-openbsd \
    curl \
    cron \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Set timezone
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Install Python dependencies
COPY requirements/production.txt .
RUN pip install --upgrade pip && \
    pip install -r production.txt

ENV FRONTEND_DIST=/opt/money_journey_frontend

# Copy project files
COPY . .
COPY --from=frontend_build /frontend/dist /opt/money_journey_frontend

# Copy supervisor configuration
COPY docker/django/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Copy entrypoint script
COPY docker/django/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Copy Gunicorn start script
COPY docker/django/start_gunicorn.sh /start_gunicorn.sh
RUN chmod +x /start_gunicorn.sh

# Set entrypoint
ENTRYPOINT [ "/entrypoint.sh" ]

# Create non-root user and set permissions
RUN useradd -m -u 1000 django && \
    mkdir -p /app/logs /app/run /app/staticfiles /app/media && \
    chown -R django:django /app

USER root

EXPOSE 8000

CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
