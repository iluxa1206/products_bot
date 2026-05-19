FROM python:3.11-slim

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование файлов проекта
COPY main1.py .
COPY product_files/ ./product_files/
COPY db.db . 2>/dev/null || true

# Создание директории для логов
RUN mkdir -p /app/logs

# Запуск бота
CMD ["python", "main1.py"]
