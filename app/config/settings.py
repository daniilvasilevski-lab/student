"""
Настройки приложения с загрузкой из переменных окружения
"""

import os
from typing import List, Optional
from pydantic import validator
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()


class Settings(BaseSettings):
    """Настройки приложения"""
    
    # === ОБЯЗАТЕЛЬНЫЕ НАСТРОЙКИ ===
    
    openai_api_key: Optional[str] = None
    
    # === НАСТРОЙКИ ПРИЛОЖЕНИЯ ===
    
    env: str = "development"
    port: int = 8000
    host: str = "0.0.0.0"
    
    # === GOOGLE SERVICES ===
    
    google_service_account_key: Optional[str] = None
    results_sheet_id: Optional[str] = None
    source_sheet_url: Optional[str] = None
    results_sheet_url: Optional[str] = None
    
    # === НАСТРОЙКИ АНАЛИЗА ===
    
    default_language: str = "ru"
    max_video_size_mb: int = 100
    video_download_timeout: int = 300
    
    # === ЛОГИРОВАНИЕ ===
    
    log_level: str = "INFO"
    log_file: Optional[str] = None
    
    # === БЕЗОПАСНОСТЬ ===
    
    secret_key: str = "default-secret-key-change-in-production"
    allowed_origins: str = "http://localhost:3000,http://localhost:8080"
    
    # === ПРОИЗВОДИТЕЛЬНОСТЬ ===
    
    workers: int = 1
    max_concurrent_analyses: int = 2
    
    # === РАСШИРЕННЫЕ НАСТРОЙКИ ===
    
    whisper_model: str = "base"
    detailed_analysis_logging: bool = False
    temp_dir: str = "/tmp/interview-analyzer"
    
    # === МОНИТОРИНГ ===
    
    sentry_dsn: Optional[str] = None
    enable_metrics: bool = False
    
    # === КЕШИРОВАНИЕ ===
    
    cache_ttl: int = 3600
    
    # === ПЛАНИРОВЩИК ЗАДАЧ ===
    
    scan_interval_minutes: int = 5
    enable_auto_processing: bool = True
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore"
    }
    
    @validator("openai_api_key")
    def validate_openai_key(cls, v):
        if v and not v.startswith("sk-"):
            raise ValueError("OpenAI API key must start with 'sk-' if provided")
        return v
    
    @validator("allowed_origins")
    def parse_allowed_origins(cls, v) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v
    
    @validator("log_level")
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()
    
    @validator("whisper_model")
    def validate_whisper_model(cls, v):
        valid_models = ["tiny", "base", "small", "medium", "large"]
        if v not in valid_models:
            raise ValueError(f"Whisper model must be one of: {valid_models}")
        return v
    
    @validator("default_language")
    def validate_language(cls, v):
        valid_languages = ["ru", "en", "pl"]
        if v not in valid_languages:
            raise ValueError(f"Language must be one of: {valid_languages}")
        return v
    
    @property
    def is_production(self) -> bool:
        """Проверка, запущено ли приложение в продакшене"""
        return self.env.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Проверка, запущено ли приложение в режиме разработки"""
        return self.env.lower() == "development"
    
    @property
    def max_video_size_bytes(self) -> int:
        """Максимальный размер видео в байтах"""
        return self.max_video_size_mb * 1024 * 1024
    
    @property
    def cors_origins(self) -> List[str]:
        """Список разрешенных origins для CORS"""
        if self.is_production:
            return self.allowed_origins
        else:
            # В режиме разработки разрешаем все origins
            return ["*"]
    
    def setup_temp_directory(self):
        """Создание временной директории если она не существует"""
        os.makedirs(self.temp_dir, exist_ok=True)
        return self.temp_dir


# Создаем глобальный экземпляр настроек
settings = Settings()

# Создаем временную директорию при загрузке модуля
settings.setup_temp_directory()


def get_settings() -> Settings:
    """Получение настроек приложения"""
    return settings


# Дополнительные настройки для различных сервисов

class LoggingSettings:
    """Настройки логирования"""
    
    @staticmethod
    def get_config() -> dict:
        """Получение конфигурации логирования"""
        config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
                "detailed": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s",
                },
            },
            "handlers": {
                "default": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {
                "level": settings.log_level,
                "handlers": ["default"],
            },
            "loggers": {
                "app": {
                    "level": settings.log_level,
                    "handlers": ["default"],
                    "propagate": False,
                },
                "uvicorn": {
                    "level": "INFO",
                    "handlers": ["default"],
                    "propagate": False,
                },
            },
        }
        
        # Добавляем файловый handler если указан путь к файлу
        if settings.log_file:
            config["handlers"]["file"] = {
                "formatter": "detailed" if settings.detailed_analysis_logging else "default",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": settings.log_file,
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
            }
            config["root"]["handlers"].append("file")
            config["loggers"]["app"]["handlers"].append("file")
        
        return config


class DatabaseSettings:
    """Настройки базы данных (если используется)"""
    
    database_url: Optional[str] = os.getenv("DATABASE_URL")
    
    @property
    def is_enabled(self) -> bool:
        return self.database_url is not None


class CacheSettings:
    """Настройки кеширования"""
    
    redis_url: Optional[str] = os.getenv("REDIS_URL")
    
    @property
    def is_enabled(self) -> bool:
        return self.redis_url is not None


class SecuritySettings:
    """Настройки безопасности"""
    
    @staticmethod
    def get_cors_config() -> dict:
        """Получение конфигурации CORS"""
        return {
            "allow_origins": settings.cors_origins,
            "allow_credentials": True,
            "allow_methods": ["*"],
            "allow_headers": ["*"],
        }


# Экспорт всех настроек
__all__ = [
    "settings",
    "get_settings",
    "Settings",
    "LoggingSettings",
    "DatabaseSettings", 
    "CacheSettings",
    "SecuritySettings"
]

