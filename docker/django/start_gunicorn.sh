#!/bin/bash

# 清理旧的日志文件（如果存在）
find /app/logs -name "*.log" -user root -exec rm -f {} \; 2>/dev/null || true

# 确保日志文件权限正确
touch /app/logs/gunicorn_access.log /app/logs/gunicorn_error.log
chown django:django /app/logs/gunicorn*.log
chmod 644 /app/logs/gunicorn*.log

# 启动 gunicorn
exec gunicorn money_journey.wsgi:application --bind 0.0.0.0:8000 --workers 3 --access-logfile /app/logs/gunicorn_access.log --error-logfile /app/logs/gunicorn_error.log
