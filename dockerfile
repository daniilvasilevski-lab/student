# Многоэтапный Dockerfile для Python Interview Analyzer

# === БАЗОВЫЙ ОБРАЗ ===
FROM python:3.11-slim as base

# Метаданные
LABEL maintainer="Interview Analyzer Team"
LABEL description="AI-powered interview analysis system"
LABEL version="1.0.0"

# Установка системных переменных
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Создание пользователя для безопасности
RUN groupadd -r appuser && useradd -r -g appuser appuser

# === ЭТАП ЗАВИСИМОСТЕЙ ===
FROM base as dependencies

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    # Системные утилиты
    curl \
    wget \
    git \
    # Аудио/видео обработка
    ffmpeg \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libglib2.0-0 \
    # Для компиляции Python пакетов
    gcc \
    g++ \
    build-essential \
    python3-dev \
    # Для работы с изображениями
    libjpeg-dev \
    libpng-dev \
    # Для работы с аудио
    libasound2-dev \
    portaudio19-dev \
    # Очистка кеша
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Обновление pip
RUN pip install --upgrade pip setuptools wheel

# Копирование requirements
COPY requirements.txt /tmp/requirements.txt

# Установка Python зависимостей
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# === ЭТАП ПРИЛОЖЕНИЯ ===
FROM dependencies as application

# Создание рабочей директории
WORKDIR /app

# Копирование исходного кода
COPY . /app/

# Создание необходимых директорий
RUN mkdir -p /app/logs \
    && mkdir -p /app/temp \
    && mkdir -p /app/uploads \
    && mkdir -p /app/data

# Установка прав доступа
RUN chown -R appuser:appuser /app

# === ПРОДАКШЕН ЭТАП ===
FROM application as production

# Переключение на непривилегированного пользователя
USER appuser

# Установка переменных окружения для продакшена
ENV ENV=production \
    PORT=8000 \
    HOST=0.0.0.0 \
    TEMP_DIR=/app/temp \
    LOG_FILE=/app/logs/interview-analyzer.log

# Открытие порта
EXPOSE 8000

# Проверка здоровья
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Запуск приложения
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# === ЭТАП РАЗРАБОТКИ ===
FROM application as development

# Установка дополнительных инструментов для разработки
RUN pip install --no-cache-dir \
    pytest-cov \
    pytest-xdist \
    black \
    isort \
    flake8 \
    mypy \
    pre-commit

# Переключение на непривилегированного пользователя
USER appuser

# Установка переменных окружения для разработки
ENV ENV=development \
    PORT=8000 \
    HOST=0.0.0.0 \
    TEMP_DIR=/app/temp \
    LOG_LEVEL=DEBUG

# Открытие порта
EXPOSE 8000

# Запуск с hot reload
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# === ЭТАП ТЕСТИРОВАНИЯ ===
FROM application as testing

# Установка тестовых зависимостей
RUN pip install --no-cache-dir \
    pytest \
    pytest-asyncio \
    pytest-cov \
    pytest-mock \
    httpx \
    factory-boy

# Переключение на непривилегированного пользователя
USER appuser

# Копирование тестов
COPY tests/ /app/tests/

# Команда для запуска тестов
CMD ["python", "-m", "pytest", "tests/", "-v", "--cov=app", "--cov-report=html", "--cov-report=term"]
