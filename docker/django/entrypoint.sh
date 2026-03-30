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

# add cron jobs
echo "Adding cron jobs..."
python manage.py crontab add

# show current cron jobs
echo "Current cron jobs:"
python manage.py crontab show

# Execute command
exec "$@"