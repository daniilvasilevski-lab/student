#!/usr/bin/env python3
"""
Терминальный монитор для Interview Analyzer
Показывает статусы работы системы в реальном времени
"""

import asyncio
import os
import time
from datetime import datetime
from typing import Dict, Any
import requests
import json
from colorama import init, Fore, Back, Style
import argparse

# Инициализация colorama для цветного вывода
init(autoreset=True)

class TerminalMonitor:
    def __init__(self, api_url: str = "http://localhost:8000", update_interval: int = 5):
        self.api_url = api_url
        self.update_interval = update_interval
        self.running = False
        
    def clear_screen(self):
        """Очистка экрана"""
        os.system('clear' if os.name == 'posix' else 'cls')
        
    def print_header(self):
        """Печать заголовка"""
        print(f"{Fore.CYAN}{Style.BRIGHT}{'='*80}")
        print(f"{Fore.CYAN}{Style.BRIGHT}🎯 INTERVIEW ANALYZER - МОНИТОР СТАТУСА")
        print(f"{Fore.CYAN}{Style.BRIGHT}{'='*80}")
        print(f"{Fore.WHITE}Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{Fore.WHITE}API: {self.api_url}")
        print(f"{Fore.CYAN}{'-'*80}")
        
    def get_system_status(self) -> Dict[str, Any]:
        """Получение статуса системы"""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=5)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            return {"status": "error", "error": str(e)}
        
        return {"status": "unknown"}
    
    def get_task_status(self) -> Dict[str, Any]:
        """Получение статуса задач"""
        try:
            response = requests.get(f"{self.api_url}/api/v1/tasks/status", timeout=5)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            return {"error": str(e)}
        
        return {}
    
    def get_unprocessed_count(self) -> int:
        """Получение количества необработанных записей"""
        try:
            response = requests.get(f"{self.api_url}/api/v1/tasks/unprocessed", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return len(data.get("candidates", []))
        except Exception:
            return 0
        
        return 0
    
    def print_system_status(self, status: Dict[str, Any]):
        """Печать статуса системы"""
        print(f"{Fore.YELLOW}{Style.BRIGHT}🖥️  СТАТУС СИСТЕМЫ:")
        
        if status.get("status") == "healthy":
            print(f"   {Fore.GREEN}✅ Система работает нормально")
        elif status.get("status") == "error":
            print(f"   {Fore.RED}❌ Ошибка: {status.get('error', 'Неизвестная ошибка')}")
        else:
            print(f"   {Fore.YELLOW}⚠️  Статус неизвестен")
            
        # Компоненты системы
        components = status.get("components", {})
        if components:
            print(f"   {Fore.CYAN}📊 Компоненты:")
            for name, component_status in components.items():
                color = Fore.GREEN if component_status == "healthy" else Fore.RED
                symbol = "✅" if component_status == "healthy" else "❌"
                print(f"      {color}{symbol} {name}: {component_status}")
    
    def print_task_status(self, task_status: Dict[str, Any]):
        """Печать статуса задач"""
        print(f"\n{Fore.YELLOW}{Style.BRIGHT}⚙️  СТАТУС ЗАДАЧ:")
        
        if "error" in task_status:
            print(f"   {Fore.RED}❌ Ошибка получения статуса: {task_status['error']}")
            return
            
        # Статус планировщика
        scheduler_running = task_status.get("scheduler_running", False)
        if scheduler_running:
            print(f"   {Fore.GREEN}✅ Планировщик задач: Запущен")
        else:
            print(f"   {Fore.YELLOW}⏸️  Планировщик задач: Остановлен")
            
        # Автоматическая обработка
        auto_processing = task_status.get("auto_processing_enabled", False)
        if auto_processing:
            print(f"   {Fore.GREEN}✅ Автообработка: Включена")
            
            # Интервал сканирования
            scan_interval = task_status.get("scan_interval_minutes", 0)
            print(f"   {Fore.CYAN}⏱️  Интервал сканирования: {scan_interval} мин")
            
            # Последнее сканирование
            last_scan = task_status.get("last_scan_time")
            if last_scan:
                print(f"   {Fore.CYAN}🔍 Последнее сканирование: {last_scan}")
        else:
            print(f"   {Fore.YELLOW}⏸️  Автообработка: Отключена")
            
        # Текущие задачи
        active_tasks = task_status.get("active_tasks", 0)
        completed_tasks = task_status.get("completed_tasks", 0)
        failed_tasks = task_status.get("failed_tasks", 0)
        
        print(f"   {Fore.CYAN}📈 Активные задачи: {active_tasks}")
        print(f"   {Fore.GREEN}✅ Завершенные: {completed_tasks}")
        print(f"   {Fore.RED}❌ Неудачные: {failed_tasks}")
    
    def print_queue_status(self, unprocessed_count: int):
        """Печать статуса очереди"""
        print(f"\n{Fore.YELLOW}{Style.BRIGHT}📋 ОЧЕРЕДЬ ОБРАБОТКИ:")
        
        if unprocessed_count > 0:
            print(f"   {Fore.YELLOW}⏳ Ожидают обработки: {unprocessed_count} интервью")
        else:
            print(f"   {Fore.GREEN}✅ Очередь пуста - все интервью обработаны")
    
    def print_controls(self):
        """Печать доступных команд"""
        print(f"\n{Fore.CYAN}{Style.BRIGHT}🎮 УПРАВЛЕНИЕ:")
        print(f"   {Fore.WHITE}Ctrl+C : Выход")
        print(f"   {Fore.WHITE}s      : Ручное сканирование")
        print(f"   {Fore.WHITE}t      : Переключить автообработку")
        print(f"   {Fore.WHITE}r      : Обновить статус")
        
    def print_footer(self):
        """Печать подвала"""
        print(f"\n{Fore.CYAN}{'-'*80}")
        print(f"{Fore.WHITE}Обновление каждые {self.update_interval} сек | API: {self.api_url}")
        print(f"{Fore.CYAN}{'='*80}")
    
    async def monitor_loop(self):
        """Основной цикл мониторинга"""
        self.running = True
        
        while self.running:
            try:
                # Очистка экрана и заголовок
                self.clear_screen()
                self.print_header()
                
                # Получение данных
                system_status = self.get_system_status()
                task_status = self.get_task_status()
                unprocessed_count = self.get_unprocessed_count()
                
                # Вывод статусов
                self.print_system_status(system_status)
                self.print_task_status(task_status)
                self.print_queue_status(unprocessed_count)
                self.print_controls()
                self.print_footer()
                
                # Ожидание
                await asyncio.sleep(self.update_interval)
                
            except KeyboardInterrupt:
                self.running = False
                break
            except Exception as e:
                print(f"{Fore.RED}Ошибка мониторинга: {e}")
                await asyncio.sleep(5)
    
    def start_manual_scan(self):
        """Запуск ручного сканирования"""
        try:
            response = requests.post(f"{self.api_url}/api/v1/tasks/scan", timeout=10)
            if response.status_code == 200:
                print(f"{Fore.GREEN}✅ Ручное сканирование запущено")
            else:
                print(f"{Fore.RED}❌ Ошибка запуска сканирования")
        except Exception as e:
            print(f"{Fore.RED}❌ Ошибка: {e}")
    
    def toggle_auto_processing(self):
        """Переключение автоматической обработки"""
        try:
            # Сначала получаем текущий статус
            task_status = self.get_task_status()
            auto_processing = task_status.get("auto_processing_enabled", False)
            
            if auto_processing:
                # Останавливаем
                response = requests.post(f"{self.api_url}/api/v1/tasks/stop", timeout=10)
                action = "остановлена"
            else:
                # Запускаем
                response = requests.post(f"{self.api_url}/api/v1/tasks/start", timeout=10)
                action = "запущена"
                
            if response.status_code == 200:
                print(f"{Fore.GREEN}✅ Автообработка {action}")
            else:
                print(f"{Fore.RED}❌ Ошибка переключения автообработки")
        except Exception as e:
            print(f"{Fore.RED}❌ Ошибка: {e}")

def main():
    parser = argparse.ArgumentParser(description='Терминальный монитор Interview Analyzer')
    parser.add_argument('--api-url', default='http://localhost:8000', 
                       help='URL API сервера (по умолчанию: http://localhost:8000)')
    parser.add_argument('--interval', type=int, default=5,
                       help='Интервал обновления в секундах (по умолчанию: 5)')
    
    args = parser.parse_args()
    
    monitor = TerminalMonitor(api_url=args.api_url, update_interval=args.interval)
    
    print(f"{Fore.CYAN}{Style.BRIGHT}🚀 Запуск терминального монитора...")
    print(f"{Fore.WHITE}Подключение к: {args.api_url}")
    print(f"{Fore.WHITE}Нажмите Ctrl+C для выхода")
    
    try:
        asyncio.run(monitor.monitor_loop())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}👋 Мониторинг остановлен")
    except Exception as e:
        print(f"\n{Fore.RED}❌ Ошибка: {e}")

if __name__ == "__main__":
    main()
