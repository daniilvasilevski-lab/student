"""
Главное приложение FastAPI для анализа интервью
"""

import logging
import os
from typing import List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from pydantic import BaseModel, Field

from .services.multimodal_analyzer import MultimodalInterviewAnalyzer
from .services.google_sheets_service import GoogleSheetsService
from .models.evaluation_criteria import InterviewAnalysis, EvaluationCriteria, CRITERIA_DESCRIPTIONS

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Глобальные переменные для сервисов
analyzer = None
sheets_service = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    global analyzer, sheets_service
    
    # Инициализация сервисов
    logger.info("Initializing services...")
    
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    
    analyzer = MultimodalInterviewAnalyzer(openai_api_key)
    sheets_service = GoogleSheetsService()
    
    logger.info("Services initialized successfully")
    
    yield
    
    # Очистка ресурсов
    logger.info("Shutting down services...")

# Создание приложения FastAPI
app = FastAPI(
    title="🤖 Interview Analyzer API",
    description="Многомодальный анализ интервью с использованием ИИ",
    version="2.0.0",
    lifespan=lifespan
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене ограничить конкретными доменами
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Модели запросов и ответов
class AnalysisRequest(BaseModel):
    video_url: str = Field(..., description="URL видео интервью")
    candidate_id: str = Field(..., description="ID кандидата")
    candidate_name: str = Field(..., description="Имя кандидата")
    preferences: str = Field("", description="Предпочтения кандидата")

class AnalysisResponse(BaseModel):
    success: bool
    analysis: InterviewAnalysis = None
    error: str = None

class CriteriaInfoResponse(BaseModel):
    success: bool
    criteria: Dict[str, Dict[str, Any]]

class StatusResponse(BaseModel):
    success: bool
    status: str
    unprocessed_count: int = 0
    services_status: Dict[str, str]

# Зависимости
def get_analyzer():
    if analyzer is None:
        raise HTTPException(status_code=503, detail="Analyzer service not initialized")
    return analyzer

def get_sheets_service():
    if sheets_service is None:
        raise HTTPException(status_code=503, detail="Google Sheets service not initialized")
    return sheets_service

# Маршруты API

@app.get("/", summary="Главная страница")
async def root():
    return {
        "message": "🤖 Interview Analyzer API v2.0",
        "description": "Многомодальный анализ интервью с ИИ",
        "features": [
            "10 критериев оценки",
            "Анализ аудио, видео и текста",
            "Невербальный анализ",
            "Интеграция с Google Sheets"
        ],
        "docs": "/docs"
    }

@app.get("/health", response_model=StatusResponse, summary="Проверка состояния")
async def health_check():
    """Проверка состояния всех сервисов"""
    services_status = {
        "analyzer": "ok" if analyzer else "not_initialized",
        "sheets_service": "ok" if sheets_service else "not_initialized",
        "openai_api": "ok" if os.getenv("OPENAI_API_KEY") else "missing_key"
    }
    
    all_ok = all(status == "ok" for status in services_status.values())
    
    return StatusResponse(
        success=all_ok,
        status="healthy" if all_ok else "degraded",
        services_status=services_status
    )

@app.get("/criteria", response_model=CriteriaInfoResponse, summary="Информация о критериях оценки")
async def get_criteria_info():
    """Получение подробной информации о всех критериях оценки"""
    criteria_dict = {}
    
    for criterion in EvaluationCriteria:
        description = CRITERIA_DESCRIPTIONS.get(criterion)
        if description:
            criteria_dict[criterion.value] = {
                "name": description.name,
                "description": description.description,
                "key_indicators": description.key_indicators,
                "verbal_aspects": description.verbal_aspects,
                "non_verbal_aspects": description.non_verbal_aspects
            }
    
    return CriteriaInfoResponse(
        success=True,
        criteria=criteria_dict
    )

@app.post("/analyze", response_model=AnalysisResponse, summary="Анализ одного интервью")
async def analyze_interview(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
    analyzer_service: MultimodalInterviewAnalyzer = Depends(get_analyzer)
):
    """Анализ одного интервью с полным мультимодальным анализом"""
    try:
        logger.info(f"Starting analysis for candidate: {request.candidate_name}")
        
        # Подготовка информации о кандидате
        candidate_info = {
            "id": request.candidate_id,
            "name": request.candidate_name,
            "preferences": request.preferences
        }
        
        # Запуск анализа
        analysis_result = await analyzer_service.analyze_interview(
            request.video_url,
            candidate_info
        )
        
        logger.info(f"Analysis completed for candidate: {request.candidate_name}")
        
        return AnalysisResponse(
            success=True,
            analysis=analysis_result
        )
        
    except Exception as e:
        logger.error(f"Analysis failed for {request.candidate_name}: {str(e)}")
        return AnalysisResponse(
            success=False,
            error=str(e)
        )

# Обработчики ошибок
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc)
        }
    )

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True if os.getenv("ENV") == "development" else False
    )