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
    echo "Checking if superuser '$DJANGO_SUPERUSER_USERNAME' already exists..."
    # 检查用户是否已存在
    if python manage.py shell -c "from django.contrib.auth.models import User; exit(0 if User.objects.filter(username='$DJANGO_SUPERUSER_USERNAME').exists() else 1)" 2>/dev/null; then
        echo "Superuser '$DJANGO_SUPERUSER_USERNAME' already exists, skipping creation."
    else
        echo "Creating superuser '$DJANGO_SUPERUSER_USERNAME'..."
        # 创建超级用户并设置密码
        python manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.filter(username='$DJANGO_SUPERUSER_USERNAME').exists():
    user = User.objects.create_superuser('$DJANGO_SUPERUSER_USERNAME', '$DJANGO_SUPERUSER_EMAIL', '$DJANGO_SUPERUSER_PASSWORD')
    print('Superuser created successfully.')
else:
    print('Superuser already exists.')
" 2>/dev/null || true
    fi
fi

# Add cron jobs
echo "Adding cron jobs..."
python manage.py crontab add

# Show current cron jobs
echo "Current cron jobs:"
python manage.py crontab show

# Execute command (supervisord)
exec "$@"
