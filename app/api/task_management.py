"""
API endpoints для управления планировщиком задач
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Dict, Any, List
import logging

from ..services.task_scheduler import TaskScheduler, task_manager, create_task_scheduler
from ..services.interview_processor import InterviewProcessor
from ..config.settings import settings


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/tasks", tags=["Task Management"])

# Глобальный планировщик
global_scheduler: TaskScheduler = None


async def get_openai_client():
    """Получение OpenAI клиента (зависимость)"""
    from openai import AsyncOpenAI
    return AsyncOpenAI(api_key=settings.openai_api_key)


async def get_scheduler() -> TaskScheduler:
    """Получение планировщика задач"""
    global global_scheduler
    if global_scheduler is None:
        openai_client = await get_openai_client()
        global_scheduler = await create_task_scheduler(openai_client)
    return global_scheduler


@router.get("/status")
async def get_task_status():
    """Получить статус планировщика задач"""
    try:
        scheduler = await get_scheduler()
        status = scheduler.get_status()
        
        return {
            "success": True,
            "status": status,
            "auto_processing_enabled": settings.enable_auto_processing,
            "scan_interval_minutes": settings.scan_interval_minutes
        }
    except Exception as e:
        logger.error(f"Error getting task status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start")
async def start_scheduler(background_tasks: BackgroundTasks):
    """Запустить автоматический планировщик"""
    try:
        scheduler = await get_scheduler()
        
        if scheduler.is_running:
            return {
                "success": False,
                "message": "Scheduler is already running"
            }
        
        # Добавляем планировщик в менеджер задач
        task_manager.add_scheduler("main", scheduler)
        
        # Запускаем в фоне
        background_tasks.add_task(scheduler.run_continuous)
        
        return {
            "success": True,
            "message": "Scheduler started successfully",
            "scan_interval_minutes": settings.scan_interval_minutes
        }
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_scheduler():
    """Остановить автоматический планировщик"""
    try:
        scheduler = await get_scheduler()
        
        if not scheduler.is_running:
            return {
                "success": False,
                "message": "Scheduler is not running"
            }
        
        scheduler.stop()
        
        return {
            "success": True,
            "message": "Scheduler stopped successfully"
        }
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scan-once")
async def run_single_scan():
    """Запустить одно сканирование вручную"""
    try:
        scheduler = await get_scheduler()
        result = await scheduler.run_once()
        
        return {
            "success": True,
            "message": "Single scan completed",
            "result": result
        }
    except Exception as e:
        logger.error(f"Error running single scan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/unprocessed")
async def list_unprocessed_interviews():
    """Получить список необработанных интервью"""
    try:
        openai_client = await get_openai_client()
        processor = InterviewProcessor(openai_client)
        
        unprocessed = await processor.scan_for_unprocessed_interviews()
        
        return {
            "success": True,
            "count": len(unprocessed),
            "interviews": [
                {
                    "id": interview["id"],
                    "name": interview.get("name", "Unknown"),
                    "video_url": interview.get("video_url", ""),
                    "created_at": interview.get("created_at", "")
                }
                for interview in unprocessed
            ]
        }
    except Exception as e:
        logger.error(f"Error listing unprocessed interviews: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process/{interview_id}")
async def process_single_interview(interview_id: str):
    """Обработать конкретное интервью вручную"""
    try:
        scheduler = await get_scheduler()
        result = await scheduler.manual_process_interview(interview_id)
        
        if result.get("success"):
            return {
                "success": True,
                "message": result["message"],
                "interview_id": result["interview_id"],
                "candidate_name": result["candidate_name"],
                "language": result["language"]
            }
        else:
            return {
                "success": False,
                "error": result["error"]
            }
    except Exception as e:
        logger.error(f"Error processing interview {interview_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_processing_statistics():
    """Получить статистику обработки"""
    try:
        scheduler = await get_scheduler()
        stats = scheduler.get_status()["stats"]
        
        # Дополнительная статистика
        openai_client = await get_openai_client()
        processor = InterviewProcessor(openai_client)
        unprocessed = await processor.scan_for_unprocessed_interviews()
        
        return {
            "success": True,
            "statistics": {
                "scheduler_stats": stats,
                "current_unprocessed_count": len(unprocessed),
                "scheduler_running": scheduler.is_running,
                "auto_processing_enabled": settings.enable_auto_processing
            }
        }
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process-batch")
async def process_batch_interviews(interview_ids: List[str]):
    """Обработать несколько интервью одновременно"""
    try:
        scheduler = await get_scheduler()
        results = []
        
        for interview_id in interview_ids:
            try:
                result = await scheduler.manual_process_interview(interview_id)
                results.append({
                    "interview_id": interview_id,
                    "result": result
                })
            except Exception as e:
                results.append({
                    "interview_id": interview_id,
                    "result": {
                        "success": False,
                        "error": str(e)
                    }
                })
        
        successful = sum(1 for r in results if r["result"].get("success"))
        failed = len(results) - successful
        
        return {
            "success": True,
            "message": f"Batch processing completed: {successful} successful, {failed} failed",
            "total_processed": len(results),
            "successful": successful,
            "failed": failed,
            "results": results
        }
    except Exception as e:
        logger.error(f"Error in batch processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs")
async def get_recent_logs(lines: int = 50):
    """Получить последние логи планировщика"""
    try:
        # Это упрощенная версия - в реальном приложении можно читать из файла логов
        scheduler = await get_scheduler()
        
        return {
            "success": True,
            "message": "Log functionality not implemented yet",
            "status": scheduler.get_status(),
            "lines_requested": lines
        }
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Проверка здоровья планировщика"""
    try:
        scheduler = await get_scheduler()
        
        # Проверяем базовые компоненты
        health_status = {
            "scheduler_initialized": scheduler.processor is not None,
            "scheduler_running": scheduler.is_running,
            "openai_configured": bool(settings.openai_api_key),
            "google_sheets_configured": bool(settings.google_service_account_key),
            "auto_processing_enabled": settings.enable_auto_processing
        }
        
        all_healthy = all(health_status.values())
        
        return {
            "success": True,
            "healthy": all_healthy,
            "status": "healthy" if all_healthy else "degraded",
            "checks": health_status,
            "timestamp": scheduler.last_scan_time.isoformat() if scheduler.last_scan_time else None
        }
    except Exception as e:
        logger.error(f"Error in health check: {e}")
        return {
            "success": False,
            "healthy": False,
            "status": "unhealthy",
            "error": str(e)
        }


# Webhook endpoints для внешней интеграции

@router.post("/webhook/process")
async def webhook_process_interview(data: Dict[str, Any]):
    """Webhook для запуска обработки от внешних систем"""
    try:
        interview_id = data.get("interview_id")
        if not interview_id:
            raise HTTPException(status_code=400, detail="interview_id is required")
        
        scheduler = await get_scheduler()
        result = await scheduler.manual_process_interview(interview_id)
        
        return {
            "success": result.get("success", False),
            "interview_id": interview_id,
            "result": result
        }
    except Exception as e:
        logger.error(f"Error in webhook processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook/scan")
async def webhook_trigger_scan():
    """Webhook для запуска сканирования от внешних систем"""
    try:
        scheduler = await get_scheduler()
        result = await scheduler.run_once()
        
        return {
            "success": True,
            "message": "Scan triggered successfully",
            "result": result
        }
    except Exception as e:
        logger.error(f"Error in webhook scan: {e}")
        raise HTTPException(status_code=500, detail=str(e))
