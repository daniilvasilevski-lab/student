#!/usr/bin/env python3
"""
Скрипт проверки системы Interview Analyzer
Проверяет все компоненты и зависимости
"""

import sys
import os
import importlib
import subprocess
from pathlib import Path

def print_status(message, status="INFO"):
    """Вывод статуса с цветом"""
    colors = {
        "OK": "\033[92m✅",      # Green
        "ERROR": "\033[91m❌",   # Red  
        "WARNING": "\033[93m⚠️", # Yellow
        "INFO": "\033[94mℹ️",    # Blue
        "RESET": "\033[0m"       # Reset
    }
    
    color = colors.get(status, colors["INFO"])
    reset = colors["RESET"]
    print(f"{color} {message}{reset}")

def check_python_version():
    """Проверка версии Python"""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 10:
        print_status(f"Python версия: {version.major}.{version.minor}.{version.micro}", "OK")
        return True
    else:
        print_status(f"Python версия: {version.major}.{version.minor}.{version.micro} (требуется 3.10+)", "ERROR")
        return False

def check_package(package_name, import_name=None):
    """Проверка установки пакета"""
    if import_name is None:
        import_name = package_name
    
    try:
        importlib.import_module(import_name)
        print_status(f"Пакет {package_name}: установлен", "OK")
        return True
    except ImportError as e:
        print_status(f"Пакет {package_name}: НЕ установлен ({str(e)})", "ERROR")
        return False

def check_system_dependencies():
    """Проверка системных зависимостей"""
    dependencies = [
        ("ffmpeg", "FFmpeg для обработки видео"),
        ("python3", "Python 3"),
        ("pip3", "Python package installer")
    ]
    
    all_ok = True
    for dep, description in dependencies:
        try:
            result = subprocess.run(
                ["which", dep], 
                capture_output=True, 
                text=True
            )
            if result.returncode == 0:
                print_status(f"Системная зависимость {dep}: найден ({result.stdout.strip()})", "OK")
            else:
                print_status(f"Системная зависимость {dep}: НЕ найден", "ERROR")
                all_ok = False
        except Exception as e:
            print_status(f"Ошибка проверки {dep}: {e}", "ERROR")
            all_ok = False
    
    return all_ok

def check_files_structure():
    """Проверка структуры файлов проекта"""
    required_files = [
        "app/main.py",
        "app/config/settings.py", 
        "app/services/integrated_analyzer.py",
        "app/services/video_processor.py",
        "app/services/audio_processor.py",
        "app/services/interview_processor.py",
        "app/services/task_scheduler.py",
        "app/api/task_management.py",
        "requirements.txt",
        ".env.example"
    ]
    
    all_ok = True
    for file_path in required_files:
        if Path(file_path).exists():
            print_status(f"Файл {file_path}: найден", "OK")
        else:
            print_status(f"Файл {file_path}: НЕ найден", "ERROR")
            all_ok = False
    
    return all_ok

def check_env_file():
    """Проверка файла окружения"""
    env_file = Path(".env")
    if env_file.exists():
        print_status("Файл .env: найден", "OK")
        
        # Проверяем ключевые переменные
        with open(env_file, 'r') as f:
            content = f.read()
            
        required_vars = ["OPENAI_API_KEY"]
        for var in required_vars:
            if var in content and not content.count(f"{var}=your-") > 0:
                print_status(f"Переменная {var}: настроена", "OK")
            else:
                print_status(f"Переменная {var}: НЕ настроена", "WARNING")
        
        return True
    else:
        print_status("Файл .env: НЕ найден (скопируйте из .env.example)", "WARNING")
        return False

def check_app_imports():
    """Проверка импортов приложения"""
    try:
        sys.path.insert(0, '.')
        
        # Проверяем основные модули
        from app.config.settings import settings
        print_status("Импорт настроек: успешен", "OK")
        
        from app.main import app
        print_status("Импорт главного приложения: успешен", "OK")
        
        return True
    except Exception as e:
        print_status(f"Ошибка импорта приложения: {e}", "ERROR")
        return False

def main():
    """Основная функция проверки"""
    print("🔍 Проверка системы Interview Analyzer")
    print("=" * 50)
    
    checks = [
        ("Версия Python", check_python_version),
        ("Системные зависимости", check_system_dependencies), 
        ("Структура файлов", check_files_structure),
        ("Файл окружения", check_env_file)
    ]
    
    # Проверяем основные компоненты
    all_passed = True
    for check_name, check_func in checks:
        print(f"\n📋 {check_name}:")
        if not check_func():
            all_passed = False
    
    # Проверяем Python пакеты
    print(f"\n📦 Python пакеты:")
    
    critical_packages = [
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn"),
        ("openai", "openai"),
        ("opencv-python", "cv2"),
        ("pandas", "pandas"),
        ("numpy", "numpy"),
        ("pydantic", "pydantic"),
        ("pydantic-settings", "pydantic_settings"),
        ("python-dotenv", "dotenv")
    ]
    
    for package, import_name in critical_packages:
        if not check_package(package, import_name):
            all_passed = False
    
    # Проверяем дополнительные пакеты
    print(f"\n🔧 Дополнительные пакеты:")
    
    optional_packages = [
        ("librosa", "librosa"),
        ("speechrecognition", "speech_recognition"),
        ("mediapipe", "mediapipe"),
        ("torch", "torch"),
        ("transformers", "transformers"),
        ("whisper", "whisper"),
        ("gspread", "gspread")
    ]
    
    for package, import_name in optional_packages:
        check_package(package, import_name)
    
    # Проверяем импорты приложения
    print(f"\n🚀 Импорты приложения:")
    if not check_app_imports():
        all_passed = False
    
    # Итоговый результат
    print("\n" + "=" * 50)
    if all_passed:
        print_status("🎉 Система готова к работе!", "OK")
        print("\nДля запуска выполните:")
        print("python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000")
    else:
        print_status("❌ Есть проблемы, требующие исправления", "ERROR")
        print("\nОбратитесь к INSTALLATION.md для решения проблем")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
