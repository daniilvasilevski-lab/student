"""
Планировщик задач для автоматической обработки интервью
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import signal
import sys

from ..config.settings import settings
from .interview_processor import InterviewProcessor


logger = logging.getLogger(__name__)


class TaskScheduler:
    """Планировщик задач для автоматической обработки интервью"""
    
    def __init__(self, openai_client):
        self.openai_client = openai_client
        self.processor = None
        self.is_running = False
        self.current_task = None
        
        # Настройки планировщика
        self.scan_interval = getattr(settings, 'scan_interval_minutes', 5) * 60  # Каждые 5 минут
        self.max_concurrent_processing = getattr(settings, 'max_concurrent_analyses', 2)
        self.last_scan_time = None
        self.stats = {
            'total_scans': 0,
            'total_processed': 0,
            'total_failed': 0,
            'last_run': None,
            'next_run': None
        }
        
        # Обработка сигналов для graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Обработчик сигналов для корректного завершения"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.is_running = False
        if self.current_task:
            self.current_task.cancel()
        sys.exit(0)
    
    async def initialize(self):
        """Инициализация планировщика"""
        try:
            self.processor = InterviewProcessor(self.openai_client)
            logger.info("Task scheduler initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize task scheduler: {e}")
            raise
    
    async def scan_and_process(self) -> Dict[str, Any]:
        """Выполняет одно сканирование и обработку"""
        try:
            self.stats['total_scans'] += 1
            self.stats['last_run'] = datetime.now().isoformat()
            
            logger.info("Starting scan and process cycle")
            
            # Запускаем обработку всех необработанных интервью
            processing_stats = await self.processor.process_all_unprocessed()
            
            # Обновляем статистику
            self.stats['total_processed'] += processing_stats.get('processed', 0)
            self.stats['total_failed'] += processing_stats.get('failed', 0)
            
            self.last_scan_time = datetime.now()
            self.stats['next_run'] = (self.last_scan_time + timedelta(seconds=self.scan_interval)).isoformat()
            
            logger.info(f"Scan cycle completed. Stats: {processing_stats}")
            
            return {
                'scan_stats': processing_stats,
                'overall_stats': self.stats
            }
            
        except Exception as e:
            logger.error(f"Error in scan and process cycle: {e}")
            self.stats['total_failed'] += 1
            return {
                'error': str(e),
                'overall_stats': self.stats
            }
    
    async def run_continuous(self):
        """Запускает непрерывное сканирование"""
        if not self.processor:
            await self.initialize()
        
        self.is_running = True
        logger.info(f"Starting continuous task scheduler (interval: {self.scan_interval} seconds)")
        
        while self.is_running:
            try:
                # Создаем задачу для сканирования
                self.current_task = asyncio.create_task(self.scan_and_process())
                
                # Выполняем сканирование
                result = await self.current_task
                
                # Логируем результаты
                if 'error' in result:
                    logger.error(f"Scan cycle failed: {result['error']}")
                else:
                    scan_stats = result.get('scan_stats', {})
                    logger.info(f"Scan cycle completed. Found: {scan_stats.get('found', 0)}, "
                              f"Processed: {scan_stats.get('processed', 0)}, "
                              f"Failed: {scan_stats.get('failed', 0)}")
                
                # Ждем до следующего сканирования
                if self.is_running:
                    logger.info(f"Waiting {self.scan_interval} seconds until next scan...")
                    await asyncio.sleep(self.scan_interval)
                
            except asyncio.CancelledError:
                logger.info("Task scheduler cancelled")
                break
            except Exception as e:
                logger.error(f"Unexpected error in task scheduler: {e}")
                # Ждем перед повторной попыткой
                if self.is_running:
                    await asyncio.sleep(60)  # Ждем минуту перед повторной попыткой
        
        logger.info("Task scheduler stopped")
    
    async def run_once(self) -> Dict[str, Any]:
        """Запускает одно сканирование (для ручного запуска)"""
        if not self.processor:
            await self.initialize()
        
        logger.info("Running single scan and process cycle")
        return await self.scan_and_process()
    
    def stop(self):
        """Останавливает планировщик"""
        logger.info("Stopping task scheduler...")
        self.is_running = False
        if self.current_task:
            self.current_task.cancel()
    
    def get_status(self) -> Dict[str, Any]:
        """Возвращает статус планировщика"""
        return {
            'is_running': self.is_running,
            'last_scan_time': self.last_scan_time.isoformat() if self.last_scan_time else None,
            'scan_interval_seconds': self.scan_interval,
            'stats': self.stats,
            'processor_configured': self.processor is not None
        }
    
    async def manual_process_interview(self, interview_id: str) -> Dict[str, Any]:
        """Ручная обработка конкретного интервью"""
        if not self.processor:
            await self.initialize()
        
        try:
            # Получаем список необработанных интервью
            unprocessed = await self.processor.scan_for_unprocessed_interviews()
            
            # Ищем интервью с нужным ID
            target_interview = None
            for interview in unprocessed:
                if interview['id'] == interview_id:
                    target_interview = interview
                    break
            
            if not target_interview:
                return {
                    'success': False,
                    'error': f'Interview with ID {interview_id} not found or already processed'
                }
            
            # Обрабатываем интервью
            result = await self.processor.process_single_interview(target_interview)
            
            if result:
                # Сохраняем результаты
                if await self.processor.save_results_to_sheet(result):
                    # Отмечаем как обработанное
                    await self.processor.mark_as_processed(target_interview)
                    
                    return {
                        'success': True,
                        'interview_id': interview_id,
                        'candidate_name': target_interview['name'],
                        'language': result['language'],
                        'message': 'Interview processed successfully'
                    }
                else:
                    return {
                        'success': False,
                        'error': 'Failed to save results to sheet'
                    }
            else:
                return {
                    'success': False,
                    'error': 'Failed to process interview'
                }
                
        except Exception as e:
            logger.error(f"Error in manual interview processing: {e}")
            return {
                'success': False,
                'error': str(e)
            }


class BackgroundTaskManager:
    """Менеджер фоновых задач"""
    
    def __init__(self):
        self.schedulers = {}
        self.background_tasks = set()
    
    def add_scheduler(self, name: str, scheduler: TaskScheduler):
        """Добавляет планировщик"""
        self.schedulers[name] = scheduler
    
    async def start_all_schedulers(self):
        """Запускает все планировщики"""
        for name, scheduler in self.schedulers.items():
            task = asyncio.create_task(scheduler.run_continuous())
            task.set_name(f"scheduler-{name}")
            self.background_tasks.add(task)
            logger.info(f"Started scheduler: {name}")
    
    async def stop_all_schedulers(self):
        """Останавливает все планировщики"""
        for name, scheduler in self.schedulers.items():
            scheduler.stop()
            logger.info(f"Stopped scheduler: {name}")
        
        # Отменяем все фоновые задачи
        for task in self.background_tasks:
            task.cancel()
        
        # Ждем завершения всех задач
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)
        
        self.background_tasks.clear()
    
    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Возвращает статус всех планировщиков"""
        return {name: scheduler.get_status() for name, scheduler in self.schedulers.items()}


# Глобальный менеджер задач
task_manager = BackgroundTaskManager()


async def create_task_scheduler(openai_client) -> TaskScheduler:
    """Фабрика для создания планировщика задач"""
    scheduler = TaskScheduler(openai_client)
    await scheduler.initialize()
    return scheduler
