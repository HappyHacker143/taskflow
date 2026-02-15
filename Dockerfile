FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем проект
COPY . .

# Собираем статические файлы
RUN python manage.py collectstatic --noinput

# Создаем непривилегированного пользователя
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Экспонируем порт
EXPOSE 8000

# Запускаем Gunicorn
CMD ["gunicorn", "taskmanager.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
