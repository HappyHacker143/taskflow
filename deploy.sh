#!/bin/bash

echo "🚀 Starting deployment..."

# Загружаем переменные окружения
set -a
source .env
set +a

# Останавливаем старые контейнеры
echo "📦 Stopping old containers..."
docker-compose -f docker-compose.prod.yml down

# Собираем новые образы
echo "🔨 Building new images..."
docker-compose -f docker-compose.prod.yml build

# Запускаем контейнеры
echo "▶️  Starting containers..."
docker-compose -f docker-compose.prod.yml up -d

# Ждём запуска базы данных
echo "⏳ Waiting for database..."
sleep 5

# Применяем миграции
echo "📊 Running migrations..."
docker-compose -f docker-compose.prod.yml exec -T web python manage.py migrate

# Собираем статические файлы
echo "📁 Collecting static files..."
docker-compose -f docker-compose.prod.yml exec -T web python manage.py collectstatic --noinput

echo "✅ Deployment complete!"
echo "🌐 Your app is running at http://$(hostname -I | awk '{print $1}'):80"
