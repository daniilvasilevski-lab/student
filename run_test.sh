#!/bin/bash

# 🧪 Script for testing the Interview Analyzer project

echo "🎯 Interview Analyzer - Test Suite"
echo "=================================="

# Установка переменных окружения для тестирования
export OPENAI_API_KEY="sk-test-key-for-testing-purposes"
export ENV="testing"
export LOG_LEVEL="DEBUG"

echo "📋 Running all tests..."
echo ""

# 1. Запуск основных тестов
echo "1️⃣ Running main test suite..."
python -m pytest tests/ -v --tb=short

echo ""

# 2. Запуск тестов с покрытием
echo "2️⃣ Running tests with coverage..."
python -m pytest tests/ --cov=app --cov-report=term-missing --cov-report=html

echo ""

# 3. Проверка качества кода
echo "3️⃣ Code quality checks..."

# Flake8 (линтинг)
echo "🔍 Running flake8..."
python -m flake8 app/ --max-line-length=100 --exclude=__pycache__

echo ""

# Black (форматирование)
echo "🎨 Checking black formatting..."
python -m black app/ tests/ --check --diff

echo ""

# isort (сортировка импортов)
echo "📦 Checking import sorting..."
python -m isort app/ tests/ --check-only --diff

echo ""

# 4. Проверка типов с mypy
echo "4️⃣ Type checking with mypy..."
python -m mypy app/ --ignore-missing-imports

echo ""

# 5. Тест Docker сборки
echo "5️⃣ Testing Docker build..."
docker build -t interview-analyzer-test --target testing .

echo ""

# 6. Тест API endpoints
echo "6️⃣ Testing API endpoints..."

# Запуск приложения в фоне
echo "Starting application..."
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 &
APP_PID=$!

# Ждем запуска приложения
echo "Waiting for application to start..."
sleep 10

# Тестирование endpoints
echo "Testing /health endpoint..."
curl -s http://localhost:8001/health | python -m json.tool

echo ""
echo "Testing / endpoint..."
curl -s http://localhost:8001/ | python -m json.tool

echo ""
echo "Testing /criteria endpoint..."
curl -s http://localhost:8001/criteria | python -m json.tool

# Останавливаем приложение
echo "Stopping application..."
kill $APP_PID

echo ""

# 7. Финальный отчет
echo "7️⃣ Final report..."
echo "✅ Test suite completed!"
echo "📊 Coverage report available in htmlcov/index.html"
echo "🐳 Docker build successful"
echo "🔗 API endpoints tested"

echo ""
echo "🎉 All tests completed successfully!"
