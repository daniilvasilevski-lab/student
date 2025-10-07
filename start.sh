#!/bin/bash

# 🚀 Interview Analyzer - Простой запуск в одном терминале
# Использование: ./start.sh

echo "🚀 INTERVIEW ANALYZER - ЗАПУСК СИСТЕМЫ"
echo "======================================"

# Проверка виртуального окружения
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  ВНИМАНИЕ: Виртуальное окружение не активировано!"
    echo "   Попытка активации: source venv/bin/activate"
    
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
        echo "✅ Виртуальное окружение активировано"
    else
        echo "❌ Файл venv/bin/activate не найден"
        echo "   Создайте виртуальное окружение: python3 -m venv venv"
        exit 1
    fi
fi

# Проверка зависимостей
echo "🔍 Проверка зависимостей..."
if ! python3 -c "import colorama" 2>/dev/null; then
    echo "📦 Установка colorama..."
    pip install colorama
fi

# Запуск unified launcher
echo "🔄 Запуск системы..."
python3 unified_launcher.py
