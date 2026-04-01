#!/bin/bash

set -e

# Function to wait for database (if needed)
wait_for_database() {
    if [ -n "$MYSQL_HOST" ] && [ -n "$MYSQL_PORT" ]; then
        echo "Waiting for database at $MYSQL_HOST:$MYSQL_PORT..."
        while ! nc -z $MYSQL_HOST $MYSQL_PORT; do
            sleep 1
        done
        echo "Database is ready!"
    else
        echo "Database host/port not specified, skipping wait..."
    fi
}

# 如果让 supervisor 管理 cron，不要在这里启动 cron
# 只需确保没有其他 cron 进程在运行
echo "Checking for existing cron processes..."
pkill cron 2>/dev/null || true
rm -f /var/run/crond.pid

# Wait for database if configured
wait_for_database

# Run database migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

# Create superuser if environment variables are set
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_EMAIL" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
    echo "Creating superuser..."
    python manage.py createsuperuser \
        --noinput \
        --username $DJANGO_SUPERUSER_USERNAME \
        --email $DJANGO_SUPERUSER_EMAIL || true
fi

# Add cron jobs
echo "Adding cron jobs..."
python manage.py crontab add

# Show current cron jobs
echo "Current cron jobs:"
python manage.py crontab show

# Execute command (supervisord)
exec "$@"
