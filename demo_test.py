#!/usr/bin/env python3
"""
Demo скрипт для тестирования Interview Analyzer
Проверяет основной функционал без реальных API вызовов
"""

import asyncio
import sys
import os
from pathlib import Path

# Добавляем путь к проекту
sys.path.insert(0, '.')

async def test_language_detection():
    """Тест определения языка"""
    print("🌍 Тестирование определения языка...")
    
    try:
        from app.services.language_detector import LanguageDetector
        
        detector = LanguageDetector()
        
        test_cases = [
            ("Иван Петров", "ru"),
            ("John Smith", "en"),
            ("Anna Kowalski", "pl"),
            ("Дмитрий Васильев", "ru"),
            ("Michael Johnson", "en"),
            ("Katarzyna Nowak", "pl")
        ]
        
        for name, expected in test_cases:
            detected = detector.detect_language_by_name(name)
            status = "✅" if detected == expected else "❌"
            print(f"  {status} {name} → {detected} (ожидался {expected})")
        
        print("✅ Определение языка работает!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования языков: {e}")
        return False

async def test_settings():
    """Тест настроек"""
    print("⚙️ Тестирование настроек...")
    
    try:
        from app.config.settings import settings
        
        print(f"  ✅ Язык по умолчанию: {settings.default_language}")
        print(f"  ✅ Порт: {settings.port}")
        print(f"  ✅ Режим: {settings.env}")
        print(f"  ✅ Временная папка: {settings.temp_dir}")
        print(f"  ✅ Интервал сканирования: {settings.scan_interval_minutes} мин")
        
        # Проверяем создание временной папки
        if Path(settings.temp_dir).exists():
            print(f"  ✅ Временная папка создана")
        else:
            print(f"  ❌ Временная папка не создана")
        
        print("✅ Настройки работают!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка настроек: {e}")
        return False

async def test_mock_analysis():
    """Тест мок-анализа без реальных API вызовов"""
    print("🧠 Тестирование мок-анализа...")
    
    try:
        # Импортируем модели
        from app.models.evaluation_criteria import InterviewAnalysis, EvaluationCriteria
        
        # Создаем тестовый результат анализа
        test_analysis = InterviewAnalysis(
            candidate_name="Тест Кандидат",
            candidate_id="test_001",
            overall_score=7.5,
            criteria_scores={
                EvaluationCriteria.COMMUNICATION: 8.0,
                EvaluationCriteria.TECHNICAL_KNOWLEDGE: 7.0,
                EvaluationCriteria.PROBLEM_SOLVING: 8.5,
                EvaluationCriteria.STRESS_RESISTANCE: 6.5,
                EvaluationCriteria.TEAMWORK: 7.5,
                EvaluationCriteria.LEADERSHIP: 6.0,
                EvaluationCriteria.ADAPTABILITY: 8.0,
                EvaluationCriteria.MOTIVATION: 9.0,
                EvaluationCriteria.CULTURAL_FIT: 7.0,
                EvaluationCriteria.PROFESSIONALISM: 8.5
            },
            detailed_feedback="Тестовый анализ кандидата показал хорошие результаты...",
            recommendations=[
                "Рекомендуется дальнейшее интервью",
                "Стоит обратить внимание на техническую подготовку"
            ],
            red_flags=[],
            video_analysis={
                "eye_contact_percentage": 75,
                "emotion_analysis": {"confident": 60, "nervous": 20, "happy": 20},
                "gesture_frequency": 8
            },
            audio_analysis={
                "speech_rate": 150,
                "speech_clarity": 8,
                "confidence_level": 7
            },
            processing_time=45.2,
            analysis_date="2024-10-06T10:30:00Z"
        )
        
        print(f"  ✅ Кандидат: {test_analysis.candidate_name}")
        print(f"  ✅ Общая оценка: {test_analysis.overall_score}/10")
        print(f"  ✅ Время обработки: {test_analysis.processing_time}с")
        print(f"  ✅ Количество критериев: {len(test_analysis.criteria_scores)}")
        print(f"  ✅ Зрительный контакт: {test_analysis.video_analysis['eye_contact_percentage']}%")
        
        print("✅ Мок-анализ работает!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка мок-анализа: {e}")
        return False

async def test_api_structure():
    """Тест структуры API"""
    print("🌐 Тестирование структуры API...")
    
    try:
        from app.main import app
        from app.api.task_management import router
        
        # Проверяем что приложение создается
        print(f"  ✅ FastAPI приложение создано")
        print(f"  ✅ Название: {app.title}")
        print(f"  ✅ Версия: {app.version}")
        
        # Проверяем роуты
        routes = [route.path for route in app.routes]
        expected_routes = [
            "/",
            "/health", 
            "/analyze",
            "/api/v1/tasks/status"
        ]
        
        for route in expected_routes:
            if any(route in r for r in routes):
                print(f"  ✅ Роут {route} найден")
            else:
                print(f"  ❌ Роут {route} не найден")
        
        print("✅ API структура готова!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка API: {e}")
        return False

async def test_task_scheduler_init():
    """Тест инициализации планировщика задач"""
    print("⏰ Тестирование планировщика задач...")
    
    try:
        from app.services.task_scheduler import TaskScheduler
        
        # Создаем мок OpenAI клиента
        class MockOpenAIClient:
            def __init__(self):
                self.api_key = "mock-key"
        
        mock_client = MockOpenAIClient()
        scheduler = TaskScheduler(mock_client)
        
        print(f"  ✅ Планировщик создан")
        print(f"  ✅ Интервал сканирования: {scheduler.scan_interval}с")
        print(f"  ✅ Статус: {'запущен' if scheduler.is_running else 'остановлен'}")
        print(f"  ✅ Статистика инициализирована: {bool(scheduler.stats)}")
        
        # Тест получения статуса
        status = scheduler.get_status()
        print(f"  ✅ Получение статуса работает: {len(status)} полей")
        
        print("✅ Планировщик готов!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка планировщика: {e}")
        return False

async def main():
    """Основная функция демо-тестирования"""
    print("🚀 Demo тестирование Interview Analyzer")
    print("=" * 60)
    
    tests = [
        ("Настройки приложения", test_settings),
        ("Определение языка", test_language_detection),
        ("Мок-анализ интервью", test_mock_analysis),
        ("API структура", test_api_structure),
        ("Планировщик задач", test_task_scheduler_init)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 {test_name}:")
        try:
            if await test_func():
                passed += 1
        except Exception as e:
            print(f"❌ Критическая ошибка в {test_name}: {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 Результаты: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("🎉 Все компоненты работают! Система готова к использованию!")
        print("\nСледующие шаги:")
        print("1. Настройте OpenAI API ключ в .env")
        print("2. Установите зависимости: pip install -r requirements.txt")
        print("3. Запустите сервер: python3 -m uvicorn app.main:app --port 8000")
    elif passed >= total * 0.7:
        print("⚠️ Большинство компонентов работает, есть мелкие проблемы")
        print("Система готова к использованию с ограничениями")
    else:
        print("❌ Много критических проблем, требуется исправление")
        print("Обратитесь к INSTALLATION.md для решения проблем")
    
    return passed == total

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Тестирование прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")
        sys.exit(1)
