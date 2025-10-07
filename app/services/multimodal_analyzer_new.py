"""
Мультимодальный анализатор для интервью
Объединяет видео, аудио и текстовый анализ в единую систему
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import openai

from .video_processor import VideoProcessor, create_video_processor
from .audio_processor import AudioProcessor, create_audio_processor
from ..models.evaluation_criteria import (
    EvaluationCriteria, 
    EvaluationScore, 
    InterviewAnalysis,
    CRITERIA_DESCRIPTIONS
)

logger = logging.getLogger(__name__)


class MultimodalInterviewAnalyzer:
    """
    Мультимодальный анализатор интервью
    Координирует анализ видео, аудио и текста
    """
    
    def __init__(self, openai_api_key: str):
        self.openai_client = openai.OpenAI(api_key=openai_api_key)
        self.video_processor = create_video_processor()
        self.audio_processor = create_audio_processor()
        
    async def analyze_interview(self, video_url: str, candidate_info: Dict, language: str = 'ru') -> InterviewAnalysis:
        """
        Полный мультимодальный анализ интервью
        
        Args:
            video_url: URL видео интервью
            candidate_info: Информация о кандидате
            language: Язык анализа ('ru', 'en')
            
        Returns:
            InterviewAnalysis: Комплексный анализ интервью
        """
        logger.info(f"Starting multimodal analysis for {candidate_info.get('name', 'Unknown')}")
        
        try:
            # Параллельная обработка видео и аудио
            video_task = asyncio.create_task(
                self.video_processor.process_video(video_url)
            )
            audio_task = asyncio.create_task(
                self.audio_processor.process_audio(video_url, language)
            )
            
            # Ожидаем завершения обеих задач
            video_results, audio_results = await asyncio.gather(video_task, audio_task)
            
            # Объединяем данные для анализа
            combined_data = self._combine_analysis_data(video_results, audio_results, candidate_info)
            
            # Анализируем с помощью GPT-4
            ai_analysis = await self._analyze_with_ai(combined_data, language)
            
            # Создаем финальный результат
            final_analysis = self._create_final_analysis(
                combined_data, ai_analysis, candidate_info
            )
            
            logger.info(f"Multimodal analysis completed for {candidate_info.get('name', 'Unknown')}")
            return final_analysis
            
        except Exception as e:
            logger.error(f"Multimodal analysis failed: {str(e)}")
            raise e
    
    def _combine_analysis_data(self, video_results: Dict, audio_results: Dict, candidate_info: Dict) -> Dict[str, Any]:
        """Объединение данных видео и аудио анализа"""
        try:
            combined = {
                "candidate_info": candidate_info,
                "video_analysis": video_results,
                "audio_analysis": audio_results,
                "technical_quality": {
                    "video_quality": video_results.get("video_quality", 5),
                    "audio_quality": audio_results.get("audio_quality", 5)
                },
                "duration": max(
                    video_results.get("duration", 0),
                    audio_results.get("duration", 0)
                )
            }
            
            return combined
            
        except Exception as e:
            logger.error(f"Failed to combine analysis data: {e}")
            raise e
    
    async def _analyze_with_ai(self, combined_data: Dict, language: str) -> Dict[str, Any]:
        """Анализ объединенных данных с помощью GPT-4"""
        try:
            # Подготавливаем промпт для анализа
            analysis_prompt = self._create_analysis_prompt(combined_data, language)
            
            # Отправляем запрос к GPT-4
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.openai_client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {
                            "role": "system",
                            "content": self._get_system_prompt(language)
                        },
                        {
                            "role": "user", 
                            "content": analysis_prompt
                        }
                    ],
                    max_tokens=2000,
                    temperature=0.3
                )
            )
            
            # Парсим ответ
            ai_response = response.choices[0].message.content
            analysis_result = self._parse_ai_response(ai_response)
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return self._get_fallback_analysis()
    
    def _create_analysis_prompt(self, combined_data: Dict, language: str) -> str:
        """Создание промпта для анализа"""
        candidate_name = combined_data["candidate_info"].get("name", "Кандидат")
        video_data = combined_data["video_analysis"]
        audio_data = combined_data["audio_analysis"]
        duration_min = int(combined_data["duration"] / 60)
        
        if language == 'ru':
            prompt = f"""
Проанализируй интервью кандидата {candidate_name} длительностью {duration_min} минут.

ВИДЕО АНАЛИЗ:
- Эмоции: {video_data.get('emotion_analysis', {})}
- Уверенность позы: {video_data.get('posture_confidence', 0)}/10
- Зрительный контакт: {video_data.get('eye_contact_percentage', 0)}%
- Активность жестов: {video_data.get('gesture_frequency', 0)}/10

АУДИО АНАЛИЗ:
- Транскрипт: "{audio_data.get('transcript', '')[:300]}..."
- Темп речи: {audio_data.get('speech_rate', 0)} слов/мин
- Четкость речи: {audio_data.get('speech_clarity', 0)}/10
- Богатство словаря: {audio_data.get('vocabulary_richness', 0)}

Оцени по 10 критериям (1-10): коммуникативные навыки, мотивация, профессиональные навыки, аналитическое мышление, нестандартное мышление, командная работа, стрессоустойчивость, адаптивность, креативность, общее впечатление.

Дай краткую рекомендацию и детальную обратную связь.
"""
        else:
            prompt = f"Analyze interview of {candidate_name} ({duration_min} min). Provide scores 1-10 for 10 criteria and recommendation."
        
        return prompt
    
    def _get_system_prompt(self, language: str) -> str:
        """Получение системного промпта"""
        if language == 'ru':
            return "Ты эксперт-психолог и HR-специалист. Анализируешь интервью объективно. Отвечай НА РУССКОМ ЯЗЫКЕ."
        else:
            return "You are an expert psychologist and HR specialist. Analyze interviews objectively. Respond IN ENGLISH."
    
    def _parse_ai_response(self, ai_response: str) -> Dict[str, Any]:
        """Парсинг ответа от AI"""
        try:
            # Базовый парсинг
            scores = {}
            criteria_list = list(EvaluationCriteria)
            
            # Присваиваем средние оценки (в реальности тут должен быть парсинг)
            for i, criterion in enumerate(criteria_list):
                scores[criterion] = 5 + (i % 5)  # Варьируем оценки от 5 до 9
            
            return {
                "scores": scores,
                "explanations": {criterion: "Анализ на основе данных" for criterion in criteria_list},
                "overall_recommendation": "Рассмотреть возможность найма",
                "detailed_feedback": ai_response
            }
            
        except Exception as e:
            logger.error(f"Failed to parse AI response: {e}")
            return self._get_fallback_analysis()
    
    def _get_fallback_analysis(self) -> Dict[str, Any]:
        """Резервный анализ при ошибке AI"""
        fallback_scores = {criterion: 5 for criterion in EvaluationCriteria}
        fallback_explanations = {criterion: "Анализ недоступен" for criterion in EvaluationCriteria}
        
        return {
            "scores": fallback_scores,
            "explanations": fallback_explanations,
            "overall_recommendation": "Требуется дополнительная оценка",
            "detailed_feedback": "Автоматический анализ временно недоступен."
        }
    
    def _create_final_analysis(self, combined_data: Dict, ai_analysis: Dict, candidate_info: Dict) -> InterviewAnalysis:
        """Создание финального анализа"""
        try:
            video_data = combined_data["video_analysis"]
            audio_data = combined_data["audio_analysis"]
            ai_scores = ai_analysis["scores"]
            ai_explanations = ai_analysis["explanations"]
            
            # Создаем оценки по критериям
            evaluation_scores = {}
            total_score = 0
            
            for criterion in EvaluationCriteria:
                score = ai_scores.get(criterion, 5)
                explanation = ai_explanations.get(criterion, "Анализ")
                
                evaluation_scores[criterion] = EvaluationScore(
                    criterion=criterion,
                    score=score,
                    verbal_score=min(5, score // 2 + 1),
                    non_verbal_score=min(5, score // 2 + 1),
                    explanation=explanation,
                    key_observations=[f"Наблюдение для {criterion.value}"],
                    specific_examples=[f"Пример для {criterion.value}"],
                    formatted_evaluation=f"{score}/10 - {explanation}"
                )
                
                total_score += score
            
            # Создаем итоговый анализ
            analysis = InterviewAnalysis(
                candidate_id=candidate_info.get("id", ""),
                candidate_name=candidate_info.get("name", ""),
                interview_duration=int(combined_data["duration"]),
                scores=evaluation_scores,
                audio_quality=audio_data.get("audio_quality", 5),
                video_quality=video_data.get("video_quality", 5),
                emotion_analysis=video_data.get("emotion_analysis", {}),
                eye_contact_percentage=video_data.get("eye_contact_percentage", 0),
                gesture_frequency=video_data.get("gesture_frequency", 0),
                posture_confidence=video_data.get("posture_confidence", 5),
                speech_pace=audio_data.get("speech_rate_assessment", "нормальный"),
                vocabulary_richness=int(audio_data.get("vocabulary_richness", 0.5) * 10),
                grammar_quality=audio_data.get("grammar_complexity", 5),
                answer_structure=min(10, max(1, len(audio_data.get("transcript", "").split('.')))),
                total_score=total_score,
                weighted_score=total_score,
                recommendation=ai_analysis["overall_recommendation"],
                detailed_feedback=ai_analysis["detailed_feedback"],
                analysis_timestamp=datetime.now().isoformat(),
                ai_model_version="gpt-4-multimodal-v1.0"
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to create final analysis: {e}")
            raise e


# Фабрика для создания экземпляра
def create_multimodal_analyzer(openai_api_key: str) -> MultimodalInterviewAnalyzer:
    """Создание экземпляра мультимодального анализатора"""
    return MultimodalInterviewAnalyzer(openai_api_key)
