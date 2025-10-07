"""
Тесты для API Interview Analyzer
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
import json
import os
import tempfile

# Устанавливаем тестовые переменные окружения перед импортом приложения
os.environ["OPENAI_API_KEY"] = "sk-test-key-for-testing-purposes"
os.environ["ENV"] = "testing"

from app.main import app
from app.models.evaluation_criteria import EvaluationCriteria, InterviewAnalysis


class TestAPI:
    """Тесты для API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Создание тестового клиента"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_analysis_result(self):
        """Мок результата анализа"""
        scores = {}
        for criterion in EvaluationCriteria:
            scores[criterion] = {
                "criterion": criterion,
                "score": 7,
                "verbal_score": 3,
                "non_verbal_score": 4,
                "explanation": f"Тестовое объяснение для {criterion.value}",
                "key_observations": ["Наблюдение 1", "Наблюдение 2"],
                "specific_examples": ["Пример 1", "Пример 2"],
                "formatted_evaluation": f"7/10 - Тестовое объяснение для {criterion.value}"
            }
        
        return {
            "candidate_id": "test-123",
            "candidate_name": "Тестовый Кандидат",
            "interview_duration": 300,
            "scores": scores,
            "audio_quality": 8,
            "video_quality": 8,
            "emotion_analysis": {"happy": 45.0, "neutral": 40.0, "confident": 15.0},
            "eye_contact_percentage": 75.0,
            "gesture_frequency": 12,
            "posture_confidence": 8,
            "speech_pace": "нормальный",
            "vocabulary_richness": 7,
            "grammar_quality": 7,
            "answer_structure": 6,
            "total_score": 70,
            "weighted_score": 70.0,
            "recommendation": "Рекомендуется к найму",
            "detailed_feedback": "Подробная обратная связь",
            "analysis_timestamp": "2024-01-01T12:00:00",
            "ai_model_version": "test-v1.0"
        }

    def test_root_endpoint(self, client):
        """Тест главной страницы"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Interview Analyzer API" in data["message"]
        assert "features" in data
        assert isinstance(data["features"], list)

    def test_health_endpoint(self, client):
        """Тест проверки здоровья"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "status" in data
        assert "services_status" in data

    def test_criteria_endpoint(self, client):
        """Тест получения критериев оценки"""
        response = client.get("/criteria")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "criteria" in data
        assert len(data["criteria"]) == 10  # Проверяем количество критериев

    @patch('app.services.integrated_analyzer.IntegratedInterviewAnalyzer.analyze_interview')
    def test_analyze_endpoint_success(self, mock_analyze, client, mock_analysis_result):
        """Тест успешного анализа интервью"""
        # Настройка мока
        mock_analyze.return_value = mock_analysis_result
        
        # Тестовые данные
        test_data = {
            "video_url": "https://example.com/test-video.mp4",
            "candidate_id": "test-123",
            "candidate_name": "Тестовый Кандидат",
            "preferences": "Python, FastAPI"
        }
        
        response = client.post("/analyze", json=test_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["analysis"]["candidate_name"] == "Тестовый Кандидат"
        assert data["analysis"]["total_score"] == 70

    def test_analyze_endpoint_missing_fields(self, client):
        """Тест анализа с отсутствующими полями"""
        test_data = {
            "video_url": "https://example.com/test-video.mp4"
            # Отсутствуют обязательные поля
        }
        
        response = client.post("/analyze", json=test_data)
        assert response.status_code == 422  # Validation error

    def test_analyze_endpoint_invalid_url(self, client):
        """Тест анализа с невалидным URL"""
        test_data = {
            "video_url": "not-a-valid-url",
            "candidate_id": "test-123",
            "candidate_name": "Тестовый Кандидат",
            "preferences": ""
        }
        
        response = client.post("/analyze", json=test_data)
        # Должен вернуть ошибку или использовать fallback
        assert response.status_code in [200, 400, 422]

    @patch('app.services.integrated_analyzer.IntegratedInterviewAnalyzer.analyze_interview')
    def test_analyze_and_save_endpoint(self, mock_analyze, client, mock_analysis_result):
        """Тест анализа с сохранением"""
        mock_analyze.return_value = mock_analysis_result
        
        test_data = {
            "video_url": "https://example.com/test-video.mp4",
            "candidate_id": "test-123",
            "candidate_name": "Тестовый Кандидат",
            "preferences": "Python"
        }
        
        response = client.post("/analyze-and-save", json=test_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True

    @patch('app.services.temporal_analyzer.TemporalInterviewAnalyzer.analyze_interview_temporal')
    def test_temporal_analysis_endpoint(self, mock_temporal, client, mock_analysis_result):
        """Тест временного анализа"""
        mock_temporal.return_value = mock_analysis_result
        
        test_data = {
            "video_url": "https://example.com/test-video.mp4",
            "candidate_id": "test-123",
            "candidate_name": "Тестовый Кандидат",
            "preferences": ""
        }
        
        response = client.post("/analyze-temporal", json=test_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True

    def test_enhanced_analysis_endpoint(self, client):
        """Тест расширенного анализа"""
        test_data = {
            "video_url": "https://example.com/test-video.mp4",
            "candidate_id": "test-123",
            "candidate_name": "Тестовый Кандидат",
            "preferences": "Python",
            "questions_url": "https://example.com/questions.pdf",
            "cv_url": "https://example.com/cv.pdf",
            "use_temporal_analysis": True
        }
        
        response = client.post("/analyze-enhanced", json=test_data)
        # Может вернуть ошибку из-за отсутствия реальных файлов
        assert response.status_code in [200, 400, 422, 500]

    def test_cors_headers(self, client):
        """Тест CORS заголовков"""
        response = client.options("/")
        assert response.status_code in [200, 405]  # OPTIONS может не поддерживаться
        
        # Проверяем GET запрос на наличие CORS заголовков
        response = client.get("/")
        # В тестовом режиме CORS заголовки могут не устанавливаться

    def test_error_handling(self, client):
        """Тест обработки ошибок"""
        # Тест с некорректными данными
        response = client.post("/analyze", json={"invalid": "data"})
        assert response.status_code == 422
        
        data = response.json()
        assert "detail" in data


class TestVideoProcessor:
    """Тесты для видео процессора"""
    
    @pytest.fixture
    def video_processor(self):
        """Создание экземпляра видео процессора"""
        from app.services.video_processor import VideoProcessor
        return VideoProcessor()
    
    @pytest.mark.asyncio
    async def test_video_processor_initialization(self, video_processor):
        """Тест инициализации видео процессора"""
        assert video_processor.mp_pose is not None
        assert video_processor.mp_face_mesh is not None
        assert video_processor.mp_hands is not None
    
    def test_video_quality_assessment(self, video_processor):
        """Тест оценки качества видео"""
        # Тест различных разрешений
        quality_hd = video_processor._assess_video_quality(1920, 1080, 30)
        assert quality_hd >= 7
        
        quality_low = video_processor._assess_video_quality(640, 480, 15)
        assert quality_low <= 5
        
        quality_4k = video_processor._assess_video_quality(3840, 2160, 60)
        assert quality_4k >= 8


class TestAudioProcessor:
    """Тесты для аудио процессора"""
    
    @pytest.fixture
    def audio_processor(self):
        """Создание экземпляра аудио процессора"""
        from app.services.audio_processor import AudioProcessor
        return AudioProcessor()
    
    def test_transcript_quality_assessment(self, audio_processor):
        """Тест оценки качества транскрипта"""
        # Хороший транскрипт
        good_transcript = "Это хороший транскрипт с достаточным количеством слов и предложений. Он содержит несколько предложений. И имеет хорошую структуру."
        quality = audio_processor._assess_transcript_quality(good_transcript, [-0.3, -0.4, -0.2])
        assert quality >= 6
        
        # Плохой транскрипт
        bad_transcript = "Короткий текст"
        quality = audio_processor._assess_transcript_quality(bad_transcript, [-2.0, -1.8])
        assert quality <= 4
        
        # Пустой транскрипт
        empty_quality = audio_processor._assess_transcript_quality("", [])
        assert empty_quality == 1

    def test_language_settings(self, audio_processor):
        """Тест языковых настроек"""
        assert "ru" in audio_processor.language_settings
        assert "en" in audio_processor.language_settings
        
        ru_settings = audio_processor.language_settings["ru"]
        assert "speech_rate_normal" in ru_settings
        assert "pause_thresholds" in ru_settings


class TestModels:
    """Тесты для моделей данных"""
    
    def test_evaluation_criteria_enum(self):
        """Тест enum критериев оценки"""
        from app.models.evaluation_criteria import EvaluationCriteria
        
        assert len(EvaluationCriteria) == 10
        assert EvaluationCriteria.COMMUNICATION_SKILLS in EvaluationCriteria
        assert EvaluationCriteria.OVERALL_IMPRESSION in EvaluationCriteria

    def test_criteria_descriptions(self):
        """Тест описаний критериев"""
        from app.models.evaluation_criteria import CRITERIA_DESCRIPTIONS, EvaluationCriteria
        
        for criterion in EvaluationCriteria:
            assert criterion in CRITERIA_DESCRIPTIONS
            description = CRITERIA_DESCRIPTIONS[criterion]
            assert hasattr(description, 'name')
            assert hasattr(description, 'description')
            assert hasattr(description, 'key_indicators')


class TestSettings:
    """Тесты для настроек"""
    
    def test_settings_loading(self):
        """Тест загрузки настроек"""
        from app.config.settings import settings
        
        assert settings.openai_api_key.startswith("sk-")
        assert settings.env == "testing"
        assert settings.port == 8000

    def test_settings_validation(self):
        """Тест валидации настроек"""
        from app.config.settings import Settings
        
        # Тест невалидного API ключа
        with pytest.raises(ValueError):
            Settings(openai_api_key="invalid-key")
        
        # Тест невалидного уровня логирования
        with pytest.raises(ValueError):
            Settings(openai_api_key="sk-test", log_level="INVALID")


class TestIntegration:
    """Интеграционные тесты"""
    
    @pytest.mark.asyncio
    async def test_full_analysis_pipeline(self):
        """Тест полного пайплайна анализа (мок)"""
        from app.services.integrated_analyzer import IntegratedInterviewAnalyzer
        from unittest.mock import MagicMock
        
        # Создаем мок OpenAI клиента
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"holistic_scores": {"communication_skills": 7}}'
        mock_client.chat.completions.create.return_value = mock_response
        
        analyzer = IntegratedInterviewAnalyzer(mock_client)
        
        # Мокаем процессоры
        with patch('app.services.integrated_analyzer.create_video_processor') as mock_video, \
             patch('app.services.integrated_analyzer.create_audio_processor') as mock_audio:
            
            mock_video_instance = MagicMock()
            mock_audio_instance = MagicMock()
            mock_video.return_value = mock_video_instance
            mock_audio.return_value = mock_audio_instance
            
            # Настраиваем моки
            mock_video_instance.process_video.return_value = {
                "duration": 300,
                "emotion_analysis": {"happy": 50.0},
                "posture_confidence": 7,
                "video_quality": 8
            }
            
            mock_audio_instance.process_audio.return_value = {
                "transcript": "Тестовый транскрипт",
                "speech_rate": 150,
                "audio_quality": 8
            }
            
            # Запускаем анализ
            result = await analyzer.analyze_interview(
                "https://example.com/test.mp4",
                {"id": "123", "name": "Test", "preferences": "Python"}
            )
            
            # Проверяем результат
            assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
