#!/usr/bin/env python3
"""
🚀 UNIFIED INTERVIEW ANALYZER LAUNCHER
Запускает сервер и мониторинг в одном терминале
"""

import os
import sys
import time
import signal
import subprocess
import threading
import requests
from datetime import datetime
from typing import Optional, Dict, Any

# Добавляем colorama для цветного вывода
try:
    from colorama import init, Fore, Back, Style
    init(autoreset=True)
except ImportError:
    # Fallback без цветов
    class MockColor:
        def __getattr__(self, name): return ""
    Fore = Back = Style = MockColor()

class UnifiedLauncher:
    """Единый launcher для запуска всей системы"""
    
    def __init__(self):
        self.server_process: Optional[subprocess.Popen] = None
        self.api_url = "http://localhost:8000"
        self.running = False
        self.auto_processing_started = False
        
        # Настройка обработки сигналов
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Обработка сигналов для корректного завершения"""
        print(f"\n{Fore.YELLOW}📤 Получен сигнал завершения...")
        self.stop()
    
    def start(self):
        """Запуск всей системы"""
        print(f"{Fore.CYAN}{Style.BRIGHT}{'='*80}")
        print(f"{Fore.CYAN}{Style.BRIGHT}🚀 INTERVIEW ANALYZER - UNIFIED LAUNCHER")
        print(f"{Fore.CYAN}{Style.BRIGHT}{'='*80}")
        print(f"{Fore.GREEN}📅 Запуск: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{Fore.GREEN}📍 API: {self.api_url}")
        print(f"{Fore.YELLOW}💡 Для остановки нажмите Ctrl+C")
        print(f"{Fore.CYAN}{'='*80}\n")
        
        # Запуск сервера
        self._start_server()
        
        # Ожидание готовности сервера
        self._wait_for_server()
        
        # Автозапуск обработки
        self._start_auto_processing()
        
        # Запуск мониторинга
        self.running = True
        self._run_monitoring()
    
    def _start_server(self):
        """Запуск FastAPI сервера"""
        print(f"{Fore.YELLOW}🔄 Запуск FastAPI сервера...")
        
        try:
            # Команда запуска сервера
            cmd = [
                sys.executable, "-m", "uvicorn", 
                "app.main:app", 
                "--host", "0.0.0.0", 
                "--port", "8000",
                "--log-level", "info"
            ]
            
            # Запуск процесса
            self.server_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Запуск потока для чтения логов сервера
            log_thread = threading.Thread(
                target=self._read_server_logs, 
                daemon=True
            )
            log_thread.start()
            
            print(f"{Fore.GREEN}✅ Сервер запущен (PID: {self.server_process.pid})")
            
        except Exception as e:
            print(f"{Fore.RED}❌ Ошибка запуска сервера: {e}")
            sys.exit(1)
    
    def _read_server_logs(self):
        """Чтение и фильтрация логов сервера"""
        if not self.server_process:
            return
            
        for line in iter(self.server_process.stdout.readline, ''):
            if not line:
                break
                
            line = line.strip()
            if not line:
                continue
                
            # Фильтрация и красивое отображение важных логов
            if "Results Google Sheets service initialized successfully" in line:
                print(f"{Fore.GREEN}📊 Google Sheets сервис инициализирован")
            elif "Services initialized successfully" in line:
                print(f"{Fore.GREEN}✅ Все сервисы запущены успешно")
            elif "Found unprocessed interview" in line:
                # Извлекаем имя кандидата
                if "Found unprocessed interview:" in line:
                    candidate = line.split("Found unprocessed interview: ")[1].split(" (Row")[0]
                    print(f"{Fore.CYAN}🔍 Найден кандидат: {candidate}")
            elif "Starting analysis for candidate" in line:
                candidate = line.split("Starting analysis for candidate: ")[1]
                print(f"{Fore.YELLOW}⚡ Начата обработка: {candidate}")
            elif "Processing interview for" in line:
                candidate = line.split("Processing interview for ")[1].split(" (ID:")[0]
                print(f"{Fore.YELLOW}🔄 Обрабатывается интервью: {candidate}")
            elif "Starting scan and process cycle" in line:
                print(f"{Fore.BLUE}🔍 Запуск цикла сканирования...")
            elif "Scan cycle completed" in line:
                print(f"{Fore.GREEN}✅ Цикл сканирования завершен")
            elif "Interview processed successfully" in line:
                print(f"{Fore.GREEN}✅ Интервью обработано успешно")
            elif "Analysis results saved" in line:
                print(f"{Fore.GREEN}💾 Результаты сохранены в Google Sheets")
            elif "Failed to process interview" in line:
                candidate = line.split("Failed to process interview for ")[1] if "Failed to process interview for" in line else "unknown"
                print(f"{Fore.RED}❌ Ошибка обработки интервью: {candidate}")
            elif "Downloading video from URL" in line:
                print(f"{Fore.CYAN}⬇️ Загрузка видео...")
            elif "Video download completed" in line:
                print(f"{Fore.GREEN}✅ Видео загружено")
            elif "Language detected" in line:
                language = line.split("Language detected: ")[1] if "Language detected: " in line else "unknown"
                print(f"{Fore.MAGENTA}🌐 Определен язык: {language}")
            elif "Analyzing video segment" in line:
                print(f"{Fore.BLUE}🎬 Анализ видеосегментов...")
            elif "Audio analysis completed" in line:
                print(f"{Fore.GREEN}🎵 Анализ аудио завершен")
            elif "Video analysis completed" in line:
                print(f"{Fore.GREEN}🎬 Анализ видео завершен")
            elif "Multimodal analysis completed" in line:
                print(f"{Fore.GREEN}🤖 Мультимодальный анализ завершен")
            elif "CV analysis completed" in line:
                print(f"{Fore.GREEN}📋 Анализ CV завершен")
            elif "Questions analysis completed" in line:
                print(f"{Fore.GREEN}❓ Анализ вопросов завершен")
            elif "Marked interview as processed" in line:
                candidate = line.split("Marked interview as processed: ")[1].split(" (Row")[0] if "Marked interview as processed:" in line else "unknown"
                print(f"{Fore.GREEN}✅ Интервью помечено как обработанное: {candidate}")
                # Показываем ошибки, но фильтруем технические детали
                if "Audio file not found after download" in line:
                    print(f"{Fore.RED}❌ Ошибка: Не удалось скачать/найти аудиофайл")
                elif "Failed to download video" in line:
                    print(f"{Fore.RED}❌ Ошибка: Не удалось скачать видео")
                elif "OpenAI API" in line:
                    print(f"{Fore.RED}❌ Ошибка API OpenAI")
                elif "Google Sheets" in line:
                    print(f"{Fore.RED}❌ Ошибка Google Sheets")
                else:
                    # Обрезаем длинные логи
                    error_msg = line[:120] + "..." if len(line) > 120 else line
                    print(f"{Fore.RED}❌ Ошибка: {error_msg}")
            elif "INFO" in line and any(keyword in line for keyword in ["Started server", "Application startup complete", "Uvicorn running"]):
                # Информационные сообщения о запуске сервера
                if "Started server process" in line:
                    print(f"{Fore.GREEN}🚀 Сервер запущен")
                elif "Application startup complete" in line:
                    print(f"{Fore.GREEN}✅ Приложение инициализировано")
                elif "Uvicorn running" in line:
                    print(f"{Fore.GREEN}🌐 API доступен на http://0.0.0.0:8000")
    
    def _wait_for_server(self):
        """Ожидание готовности сервера"""
        print(f"{Fore.YELLOW}⏳ Ожидание готовности сервера...")
        
        max_attempts = 30
        for attempt in range(max_attempts):
            try:
                response = requests.get(f"{self.api_url}/health", timeout=2)
                if response.status_code == 200:
                    print(f"{Fore.GREEN}✅ Сервер готов к работе!")
                    return
            except requests.exceptions.RequestException:
                pass
            
            time.sleep(1)
            print(f"{Fore.YELLOW}⏳ Попытка {attempt + 1}/{max_attempts}...")
        
        print(f"{Fore.RED}❌ Сервер не отвечает после {max_attempts} попыток")
        sys.exit(1)
    
    def _start_auto_processing(self):
        """Автозапуск обработки"""
        try:
            response = requests.post(f"{self.api_url}/api/v1/tasks/start")
            if response.status_code == 200:
                print(f"{Fore.GREEN}🚀 Автоматическая обработка запущена")
                self.auto_processing_started = True
            else:
                print(f"{Fore.YELLOW}⚠️  Не удалось запустить автообработку: {response.text}")
        except Exception as e:
            print(f"{Fore.YELLOW}⚠️  Ошибка запуска автообработки: {e}")
    
    def _run_monitoring(self):
        """Основной цикл мониторинга"""
        print(f"{Fore.CYAN}{'='*80}")
        print(f"{Fore.CYAN}{Style.BRIGHT}📊 МОНИТОРИНГ СИСТЕМЫ")
        print(f"{Fore.CYAN}{'='*80}\n")
        
        last_update = None
        
        while self.running:
            try:
                # Получение статуса системы
                system_status = self._get_system_status()
                task_status = self._get_task_status()
                unprocessed = self._get_unprocessed_count()
                unprocessed_details = self._get_unprocessed_details()
                
                # Очистка экрана для обновления (только статусной части)
                current_time = datetime.now().strftime('%H:%M:%S')
                
                # Обновляем только если есть изменения
                status_info = {
                    'system': system_status,
                    'tasks': task_status,
                    'unprocessed': unprocessed,
                    'unprocessed_details': unprocessed_details,
                    'time': current_time
                }
                
                if last_update != status_info:
                    self._display_status(status_info)
                    last_update = status_info.copy()
                
                # Интервал обновления
                time.sleep(5)
                
            except requests.exceptions.RequestException:
                if self.running:  # Показываем ошибку только если еще работаем
                    print(f"{Fore.RED}⚠️  Потеряна связь с сервером")
                time.sleep(2)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"{Fore.RED}❌ Ошибка мониторинга: {e}")
                time.sleep(5)
    
    def _display_status(self, status_info):
        """Отображение текущего статуса"""
        print(f"\n{Fore.CYAN}{'─'*60}")
        print(f"{Fore.CYAN}⏰ Обновление: {status_info['time']}")
        print(f"{Fore.CYAN}{'─'*60}")
        
        # Статус системы
        system = status_info['system']
        if system and system.get('status') == 'healthy':
            print(f"{Fore.GREEN}🖥️  Система: Работает нормально")
            
            # Компоненты
            components = system.get('components', {})
            for name, status in components.items():
                icon = "✅" if status == "healthy" else "❌"
                print(f"   {icon} {name}: {status}")
        else:
            print(f"{Fore.RED}🖥️  Система: Недоступна")
        
        # Статус задач
        tasks = status_info['tasks']
        if tasks:
            scheduler_status = tasks.get('scheduler_status', 'unknown')
            auto_processing = tasks.get('auto_processing_enabled', False)
            active_tasks = tasks.get('active_tasks', 0)
            completed_tasks = tasks.get('completed_tasks', 0)
            failed_tasks = tasks.get('failed_tasks', 0)
            
            print(f"\n{Fore.BLUE}⚙️  Задачи:")
            
            # Статус планировщика
            scheduler_icon = "✅" if scheduler_status == "running" else "❌"
            print(f"   {scheduler_icon} Планировщик: {scheduler_status}")
            
            # Автообработка
            auto_icon = "✅" if auto_processing else "❌"
            auto_text = "Включена" if auto_processing else "Выключена"
            print(f"   {auto_icon} Автообработка: {auto_text}")
            
            # Статистика задач
            print(f"   📈 Активные: {active_tasks}")
            print(f"   ✅ Завершенные: {completed_tasks}")
            if failed_tasks > 0:
                print(f"   ❌ Неудачные: {failed_tasks}")
        
        # Очередь обработки
        unprocessed = status_info['unprocessed']
        print(f"\n{Fore.MAGENTA}📋 Очередь:")
        if unprocessed and unprocessed > 0:
            print(f"   ⏳ Ожидают обработки: {unprocessed} интервью")
        else:
            print(f"   ✅ Очередь пуста - все интервью обработаны")
        
        # Показываем детали ожидающих интервью
        if unprocessed and unprocessed > 0:
            unprocessed_details = status_info.get('unprocessed_details', [])
            # Показываем первые 3 интервью для избежания засорения экрана
            for i, interview in enumerate(unprocessed_details[:3]):
                name = interview.get('name', 'Неизвестно')
                interview_id = interview.get('id', 'N/A')
                print(f"   • {name} (ID: {interview_id})")
            if len(unprocessed_details) > 3:
                print(f"   ... и ещё {len(unprocessed_details) - 3} интервью")
    
    def _get_system_status(self) -> Optional[Dict[str, Any]]:
        """Получение статуса системы"""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=3)
            return response.json() if response.status_code == 200 else None
        except:
            return None
    
    def _get_task_status(self) -> Optional[Dict[str, Any]]:
        """Получение статуса задач"""
        try:
            response = requests.get(f"{self.api_url}/api/v1/tasks/status", timeout=3)
            return response.json() if response.status_code == 200 else None
        except:
            return None
    
    def _get_unprocessed_count(self) -> int:
        """Получение количества необработанных интервью"""
        try:
            response = requests.get(f"{self.api_url}/api/v1/tasks/unprocessed", timeout=3)
            if response.status_code == 200:
                data = response.json()
                return data.get('count', 0)
            return 0
        except:
            return 0
    
    def _get_unprocessed_details(self) -> list:
        """Получение детальной информации о необработанных интервью"""
        try:
            response = requests.get(f"{self.api_url}/api/v1/tasks/unprocessed", timeout=3)
            if response.status_code == 200:
                data = response.json()
                return data.get('interviews', [])
            return []
        except:
            return []
    
    def stop(self):
        """Остановка всей системы"""
        print(f"\n{Fore.YELLOW}🛑 Остановка системы...")
        
        # Остановка мониторинга
        self.running = False
        
        # Остановка автообработки
        if self.auto_processing_started:
            try:
                requests.post(f"{self.api_url}/api/v1/tasks/stop", timeout=3)
                print(f"{Fore.GREEN}✅ Автообработка остановлена")
            except:
                pass
        
        # Остановка сервера
        if self.server_process:
            print(f"{Fore.YELLOW}🔄 Завершение сервера...")
            self.server_process.terminate()
            
            # Ждем корректного завершения
            try:
                self.server_process.wait(timeout=10)
                print(f"{Fore.GREEN}✅ Сервер остановлен")
            except subprocess.TimeoutExpired:
                print(f"{Fore.YELLOW}⚠️  Принудительное завершение сервера...")
                self.server_process.kill()
                self.server_process.wait()
        
        print(f"{Fore.CYAN}{'='*80}")
        print(f"{Fore.CYAN}{Style.BRIGHT}👋 СИСТЕМА ОСТАНОВЛЕНА")
        print(f"{Fore.CYAN}{'='*80}")
        sys.exit(0)

def main():
    """Главная функция"""
    # Проверка, что мы в правильной директории
    if not os.path.exists("app/main.py"):
        print(f"{Fore.RED}❌ Запустите скрипт из корня проекта (где находится app/main.py)")
        sys.exit(1)
    
    # Проверка виртуального окружения
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print(f"{Fore.YELLOW}⚠️  ВНИМАНИЕ: Виртуальное окружение не активировано!")
        print(f"{Fore.YELLOW}   Рекомендуется запустить: source venv/bin/activate")
        print(f"{Fore.YELLOW}   Продолжить? (y/n): ", end='')
        
        if input().lower() != 'y':
            sys.exit(1)
    
    # Запуск системы
    launcher = UnifiedLauncher()
    try:
        launcher.start()
    except KeyboardInterrupt:
        launcher.stop()
    except Exception as e:
        print(f"{Fore.RED}❌ Критическая ошибка: {e}")
        launcher.stop()

if __name__ == "__main__":
    main()
