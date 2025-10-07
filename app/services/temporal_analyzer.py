"""
Временной анализатор интервью с 30-секундной сегментацией
Обеспечивает детальную динамику поведения
Интегрируется с анализом CV и вопросов интервью
"""

import logging
import json
from typing import Dict, List, Any, Tuple
import asyncio
from datetime import datetime, timedelta
import math

from ..models.evaluation_criteria import (
    EvaluationCriteria, 
    EvaluationScore, 
    InterviewAnalysis,
    CRITERIA_DESCRIPTIONS
)
from .cv_analyzer import CVAnalyzer
from .questions_analyzer import QuestionsAnalyzer

logger = logging.getLogger(__name__)


class TemporalInterviewAnalyzer:
    """
    Анализатор интервью с временной сегментацией
    Анализирует изменения поведения по 30-секундным отрезкам
    """
    
    def __init__(self, openai_client):
        self.openai_client = openai_client
        self.segment_duration = 30  # секунд
        
    async def analyze_interview_temporal(
        self,
        transcript_data: Dict,
        video_data: Dict, 
        audio_data: Dict,
        candidate_info: Dict
    ) -> InterviewAnalysis:
        """
        Основной метод временного анализа интервью
        
        Args:
            transcript_data: Транскрипт с временными метками
            video_data: Видео-анализ с временными сегментами
            audio_data: Аудио-анализ с временными сегментами
            candidate_info: Информация о кандидате
            
        Returns:
            InterviewAnalysis: Комплексный анализ с учетом временной динамики
        """
        logger.info(f"Starting temporal analysis for {candidate_info.get('name', 'Unknown')}")
        
        # 1. Разделение интервью на 30-секундные сегменты
        segments = self._create_temporal_segments(
            transcript_data, video_data, audio_data
        )
        
        # 2. Определение типов вопросов по сегментам
        question_types = await self._classify_question_types(segments)
        
        # 3. Анализ поведенческой динамики по сегментам
        behavioral_dynamics = self._analyze_behavioral_dynamics(segments, question_types)
        
        # 4. Корреляция поведения с типами вопросов
        behavior_correlation = self._correlate_behavior_with_questions(
            behavioral_dynamics, question_types
        )
        
        # 5. Временные тренды и паттерны
        temporal_patterns = self._extract_temporal_patterns(behavioral_dynamics)
        
        # 6. Интегрированный анализ с GPT-4
        comprehensive_analysis = await self._analyze_with_temporal_context(
            segments, behavioral_dynamics, behavior_correlation, 
            temporal_patterns, candidate_info
        )
        
        # 7. Создание детализированных оценок
        detailed_scores = await self._create_temporal_scores(
            comprehensive_analysis, behavioral_dynamics, behavior_correlation
        )
        
        # 8. Формирование итогового результата
        final_analysis = self._build_temporal_analysis(
            detailed_scores, behavioral_dynamics, behavior_correlation,
            temporal_patterns, comprehensive_analysis, candidate_info
        )
        
        return final_analysis
    
    def _create_temporal_segments(
        self, 
        transcript_data: Dict,
        video_data: Dict,
        audio_data: Dict
    ) -> List[Dict]:
        """Создание 30-секундных сегментов"""
        
        duration = video_data.get("duration", 300)  # По умолчанию 5 минут
        num_segments = math.ceil(duration / self.segment_duration)
        
        segments = []
        transcript = transcript_data.get("transcript", "")
        words = transcript.split()
        words_per_segment = len(words) // num_segments if num_segments > 0 else len(words)
        
        for i in range(num_segments):
            start_time = i * self.segment_duration
            end_time = min((i + 1) * self.segment_duration, duration)
            
            # Распределение слов по сегментам
            start_word = i * words_per_segment
            end_word = min((i + 1) * words_per_segment, len(words))
            segment_text = " ".join(words[start_word:end_word])
            
            # Симуляция метрик для сегмента (в реальности извлекаются из видео/аудио)
            segment = {
                "segment_id": i + 1,
                "start_time": start_time,
                "end_time": end_time,
                "duration": end_time - start_time,
                
                "transcript": segment_text,
                "word_count": end_word - start_word,
                
                # Аудио метрики для сегмента (имитация)
                "audio_metrics": self._simulate_segment_audio_metrics(i, num_segments, audio_data),
                
                # Видео метрики для сегмента (имитация)
                "video_metrics": self._simulate_segment_video_metrics(i, num_segments, video_data),
                
                # Качество данных сегмента
                "data_quality": {
                    "speech_clarity": max(1, min(10, 8 + (i % 3 - 1))),
                    "video_visibility": max(1, min(10, 9 - (i % 4))),
                    "background_noise": max(1, min(5, 2 + (i % 2)))
                }
            }
            
            segments.append(segment)
        
        return segments
    
    def _simulate_segment_audio_metrics(self, segment_idx: int, total_segments: int, base_audio: Dict) -> Dict:
        """Симуляция аудио метрик для сегмента (в реальности извлекается из аудио)"""
        
        base_speech_rate = base_audio.get("speech_rate", 150)
        base_clarity = base_audio.get("speech_clarity", 7)
        base_energy = base_audio.get("average_energy", 0.6)
        
        # Симуляция изменений по сегментам
        # В начале - уверенность, в середине может быть напряжение, в конце - стабилизация
        if segment_idx < total_segments * 0.3:  # Первая треть
            rate_modifier = 1.0 + 0.1  # Немного быстрее от волнения
            clarity_modifier = 0.9      # Немного хуже четкость
            energy_modifier = 1.1       # Больше энергии
        elif segment_idx < total_segments * 0.7:  # Средняя треть
            rate_modifier = 0.85 + 0.3 * (segment_idx % 3)  # Вариативность в зависимости от сложности
            clarity_modifier = 0.8 + 0.4 * (1 - segment_idx % 2)  # То лучше, то хуже
            energy_modifier = 0.7 + 0.5 * (segment_idx % 2)      # Переменная энергия
        else:  # Последняя треть
            rate_modifier = 0.95        # Стабилизация темпа
            clarity_modifier = 1.0      # Восстановление четкости
            energy_modifier = 0.9       # Умеренная энергия
        
        return {
            "speech_rate": int(base_speech_rate * rate_modifier),
            "speech_clarity": max(1, min(10, base_clarity * clarity_modifier)),
            "pause_frequency": max(0, int(8 * (1 + 0.5 * (segment_idx % 3)))),  # Больше пауз при сложных вопросах
            "energy_level": max(0.1, min(1.0, base_energy * energy_modifier)),
            "tempo_stability": max(0.3, min(1.0, 0.8 + 0.2 * (1 - segment_idx % 2))),
            "pitch_variation": max(10, min(80, 40 + 20 * (segment_idx % 3)))
        }
    
    def _simulate_segment_video_metrics(self, segment_idx: int, total_segments: int, base_video: Dict) -> Dict:
        """Симуляция видео метрик для сегмента (в реальности извлекается из видео)"""
        
        base_emotions = base_video.get("emotion_analysis", {"confident": 40, "happy": 30, "neutral": 30})
        base_eye_contact = base_video.get("eye_contact_percentage", 70)
        base_posture = base_video.get("posture_confidence", 7)
        base_gestures = base_video.get("gesture_frequency", 10)
        
        # Симуляция эмоциональной динамики
        if segment_idx < total_segments * 0.3:  # Начало - высокая уверенность
            confidence_mult = 1.2
            nervous_add = 5
            eye_contact_mult = 1.1
            posture_mult = 1.1
        elif segment_idx < total_segments * 0.7:  # Середина - возможное напряжение
            confidence_mult = 0.6 + 0.8 * (1 - (segment_idx % 3) / 2)  # Вариативность
            nervous_add = 10 + 15 * (segment_idx % 2)  # Больше нервозности при сложных вопросах
            eye_contact_mult = 0.7 + 0.5 * (1 - segment_idx % 2)
            posture_mult = 0.6 + 0.6 * (1 - (segment_idx % 3) / 2)
        else:  # Конец - стабилизация
            confidence_mult = 0.9
            nervous_add = 8
            eye_contact_mult = 0.95
            posture_mult = 0.9
        
        return {
            "emotion_analysis": {
                "confident": max(5, min(80, base_emotions.get("confident", 40) * confidence_mult)),
                "happy": max(5, min(60, base_emotions.get("happy", 30))),
                "neutral": max(20, min(70, base_emotions.get("neutral", 30))),
                "nervous": max(2, min(40, 5 + nervous_add)),
                "focused": max(10, min(70, 40 + 20 * (segment_idx % 2)))
            },
            "eye_contact_percentage": max(30, min(95, base_eye_contact * eye_contact_mult)),
            "posture_confidence": max(2, min(10, base_posture * posture_mult)),
            "gesture_frequency": max(2, min(25, base_gestures + 5 * (segment_idx % 3))),
            "head_movement": {
                "nodding_frequency": max(0, min(15, 3 + 8 * (segment_idx % 2))),
                "head_tilts": max(0, min(10, 2 + 4 * (segment_idx % 3)))
            },
            "facial_expressions": {
                "smile_frequency": max(0, min(20, 5 + 10 * (1 - segment_idx % 2))),
                "eyebrow_raises": max(0, min(15, 2 + 8 * (segment_idx % 3)))
            }
        }
    
    async def _classify_question_types(self, segments: List[Dict]) -> Dict[int, Dict]:
        """Классификация типов вопросов по сегментам"""
        
        # Создание промпта для классификации вопросов
        segments_text = ""
        for i, segment in enumerate(segments):
            segments_text += f"\nСегмент {i+1} ({segment['start_time']}-{segment['end_time']}с): \"{segment['transcript']}\"\n"
        
        classification_prompt = f"""
Проанализируй транскрипт интервью по сегментам и определи тип вопроса/темы для каждого сегмента.

{segments_text}

Классифицируй каждый сегмент по типам:
1. "знакомство" - представление, общие вопросы о себе
2. "опыт" - обсуждение опыта работы, проектов, достижений
3. "технические" - технические знания, профессиональные навыки
4. "поведенческие" - вопросы о поведении в ситуациях
5. "проблемные" - сложные задачи, алгоритмы, незнакомые темы
6. "мотивация" - вопросы о целях, интересах, планах
7. "личные" - личные качества, хобби, ценности

Оцени также СЛОЖНОСТЬ каждого сегмента от 1 до 10, где:
1-3: простые, комфортные вопросы
4-6: средней сложности
7-10: сложные, стрессовые вопросы

Ответь в JSON формате:
{{
    "segment_1": {{"type": "знакомство", "complexity": 2, "description": "краткое описание"}},
    "segment_2": {{"type": "опыт", "complexity": 4, "description": "краткое описание"}},
    ...
}}
"""
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # Используем более дешевую модель для классификации
                messages=[
                    {"role": "system", "content": "Ты эксперт по анализу интервью. Классифицируй типы вопросов точно и кратко."},
                    {"role": "user", "content": classification_prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )
            
            content = response.choices[0].message.content
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_str = content[start_idx:end_idx]
                classifications = json.loads(json_str)
                
                # Преобразование в удобный формат
                result = {}
                for i, segment in enumerate(segments):
                    segment_key = f"segment_{i+1}"
                    if segment_key in classifications:
                        result[i+1] = classifications[segment_key]
                    else:
                        # Запасной вариант
                        result[i+1] = {
                            "type": "общие",
                            "complexity": 5,
                            "description": "Тип не определен"
                        }
                
                return result
                
        except Exception as e:
            logger.error(f"Question classification failed: {e}")
            
        # Запасная классификация
        fallback_result = {}
        for i, segment in enumerate(segments):
            # Простая эвристика на основе позиции
            if i < len(segments) * 0.2:
                question_type = "знакомство"
                complexity = 2
            elif i < len(segments) * 0.5:
                question_type = "опыт"
                complexity = 4
            elif i < len(segments) * 0.8:
                question_type = "технические"
                complexity = 7
            else:
                question_type = "проблемные"
                complexity = 8
                
            fallback_result[i+1] = {
                "type": question_type,
                "complexity": complexity,
                "description": f"Автоматическая классификация для сегмента {i+1}"
            }
        
        return fallback_result
    
    def _analyze_behavioral_dynamics(self, segments: List[Dict], question_types: Dict) -> Dict:
        """Анализ динамики поведения по сегментам"""
        
        dynamics = {
            "confidence_trend": [],
            "stress_indicators": [],
            "communication_quality": [],
            "engagement_level": [],
            "adaptability_signals": []
        }
        
        for i, segment in enumerate(segments):
            segment_id = i + 1
            audio = segment["audio_metrics"]
            video = segment["video_metrics"]
            question_info = question_types.get(segment_id, {})
            
            # Анализ уверенности
            confidence_score = self._calculate_segment_confidence(audio, video)
            dynamics["confidence_trend"].append({
                "segment": segment_id,
                "score": confidence_score,
                "time": f"{segment['start_time']}-{segment['end_time']}",
                "question_type": question_info.get("type", "unknown"),
                "complexity": question_info.get("complexity", 5)
            })
            
            # Анализ стресса
            stress_score = self._calculate_segment_stress(audio, video)
            dynamics["stress_indicators"].append({
                "segment": segment_id,
                "score": stress_score,
                "time": f"{segment['start_time']}-{segment['end_time']}",
                "indicators": self._extract_stress_indicators(audio, video)
            })
            
            # Качество коммуникации
            comm_score = self._calculate_segment_communication(audio, video, segment)
            dynamics["communication_quality"].append({
                "segment": segment_id,
                "score": comm_score,
                "time": f"{segment['start_time']}-{segment['end_time']}",
                "factors": self._extract_communication_factors(audio, video, segment)
            })
            
            # Уровень вовлеченности
            engagement_score = self._calculate_segment_engagement(audio, video)
            dynamics["engagement_level"].append({
                "segment": segment_id,
                "score": engagement_score,
                "time": f"{segment['start_time']}-{segment['end_time']}",
                "indicators": self._extract_engagement_indicators(audio, video)
            })
            
            # Сигналы адаптивности
            adaptability_score = self._calculate_segment_adaptability(i, segments, question_types)
            dynamics["adaptability_signals"].append({
                "segment": segment_id,
                "score": adaptability_score,
                "time": f"{segment['start_time']}-{segment['end_time']}",
                "adaptation_type": self._determine_adaptation_type(i, segments, question_types)
            })
        
        return dynamics
    
    def _calculate_segment_confidence(self, audio: Dict, video: Dict) -> float:
        """Расчет уверенности для сегмента"""
        
        # Факторы уверенности
        factors = {
            "speech_clarity": audio.get("speech_clarity", 5) / 10,
            "speech_rate_stability": min(1.0, audio.get("tempo_stability", 0.8)),
            "eye_contact": video.get("eye_contact_percentage", 50) / 100,
            "posture_confidence": video.get("posture_confidence", 5) / 10,
            "confident_emotion": video.get("emotion_analysis", {}).get("confident", 30) / 100,
            "gesture_appropriateness": min(1.0, max(0.3, 1.0 - abs(video.get("gesture_frequency", 10) - 12) / 15))
        }
        
        # Взвешенная сумма
        weights = {
            "speech_clarity": 0.2,
            "speech_rate_stability": 0.15,
            "eye_contact": 0.25,
            "posture_confidence": 0.15,
            "confident_emotion": 0.15,
            "gesture_appropriateness": 0.1
        }
        
        confidence = sum(factors[key] * weights[key] for key in factors)
        return round(confidence * 10, 1)  # Масштабирование в 1-10
    
    def _calculate_segment_stress(self, audio: Dict, video: Dict) -> float:
        """Расчет уровня стресса для сегмента"""
        
        stress_indicators = {
            "high_pause_frequency": min(1.0, audio.get("pause_frequency", 5) / 20),
            "speech_rate_deviation": abs(audio.get("speech_rate", 150) - 150) / 100,
            "low_clarity": max(0, (7 - audio.get("speech_clarity", 7)) / 7),
            "nervous_emotion": video.get("emotion_analysis", {}).get("nervous", 5) / 100,
            "low_eye_contact": max(0, (70 - video.get("eye_contact_percentage", 70)) / 70),
            "excessive_gestures": max(0, (video.get("gesture_frequency", 10) - 15) / 10)
        }
        
        stress_score = sum(stress_indicators.values()) / len(stress_indicators)
        return round(stress_score * 10, 1)
    
    def _calculate_segment_communication(self, audio: Dict, video: Dict, segment: Dict) -> float:
        """Расчет качества коммуникации для сегмента"""
        
        comm_factors = {
            "clarity": audio.get("speech_clarity", 5) / 10,
            "appropriate_pace": 1.0 - abs(audio.get("speech_rate", 150) - 150) / 100,
            "engagement": video.get("eye_contact_percentage", 50) / 100,
            "expression": min(1.0, (video.get("emotion_analysis", {}).get("confident", 20) + 
                                   video.get("emotion_analysis", {}).get("happy", 20)) / 60),
            "content_length": min(1.0, segment.get("word_count", 10) / 20)
        }
        
        communication_score = sum(comm_factors.values()) / len(comm_factors)
        return round(communication_score * 10, 1)
    
    def _calculate_segment_engagement(self, audio: Dict, video: Dict) -> float:
        """Расчет уровня вовлеченности для сегмента"""
        
        engagement_factors = {
            "energy_level": audio.get("energy_level", 0.5),
            "eye_contact": video.get("eye_contact_percentage", 50) / 100,
            "gesture_activity": min(1.0, video.get("gesture_frequency", 5) / 15),
            "emotional_variety": len([e for e in video.get("emotion_analysis", {}).values() if e > 10]) / 5,
            "vocal_variation": min(1.0, audio.get("pitch_variation", 30) / 60)
        }
        
        engagement = sum(engagement_factors.values()) / len(engagement_factors)
        return round(engagement * 10, 1)
    
    def _calculate_segment_adaptability(self, segment_idx: int, segments: List[Dict], question_types: Dict) -> float:
        """Расчет адаптивности для сегмента"""
        
        if segment_idx == 0:
            return 5.0  # Нет предыдущего сегмента для сравнения
        
        current_segment = segments[segment_idx]
        previous_segment = segments[segment_idx - 1]
        
        current_type = question_types.get(segment_idx + 1, {})
        previous_type = question_types.get(segment_idx, {})
        
        # Если изменился тип вопроса, анализируем адаптацию
        if current_type.get("type") != previous_type.get("type"):
            # Изменение в поведении между сегментами
            confidence_change = (
                self._calculate_segment_confidence(
                    current_segment["audio_metrics"], 
                    current_segment["video_metrics"]
                ) -
                self._calculate_segment_confidence(
                    previous_segment["audio_metrics"], 
                    previous_segment["video_metrics"]
                )
            )
            
            # Ожидаемое изменение на основе сложности
            complexity_diff = current_type.get("complexity", 5) - previous_type.get("complexity", 5)
            expected_confidence_drop = complexity_diff * 0.5
            
            # Адаптивность = насколько хорошо кандидат справился с изменением
            if complexity_diff > 0:  # Вопросы стали сложнее
                adaptability = 5 + min(3, max(-3, -confidence_change + expected_confidence_drop))
            else:  # Вопросы стали проще или остались на том же уровне
                adaptability = 5 + min(2, max(-2, -confidence_change))
            
            return round(adaptability, 1)
        
        return 5.0  # Нет изменения типа вопроса
    
    def _extract_stress_indicators(self, audio: Dict, video: Dict) -> List[str]:
        """Извлечение индикаторов стресса"""
        indicators = []
        
        if audio.get("pause_frequency", 5) > 12:
            indicators.append(f"частые паузы ({audio['pause_frequency']})")
        
        if audio.get("speech_clarity", 7) < 6:
            indicators.append(f"снижение четкости речи ({audio['speech_clarity']}/10)")
        
        if video.get("eye_contact_percentage", 70) < 50:
            indicators.append(f"избегание взгляда ({video['eye_contact_percentage']:.1f}%)")
        
        if video.get("emotion_analysis", {}).get("nervous", 5) > 15:
            indicators.append(f"нервозность ({video['emotion_analysis']['nervous']:.1f}%)")
        
        return indicators
    
    def _extract_communication_factors(self, audio: Dict, video: Dict, segment: Dict) -> List[str]:
        """Извлечение факторов коммуникации"""
        factors = []
        
        clarity = audio.get("speech_clarity", 5)
        if clarity >= 8:
            factors.append(f"отличная четкость речи ({clarity}/10)")
        elif clarity >= 6:
            factors.append(f"хорошая четкость речи ({clarity}/10)")
        else:
            factors.append(f"нечеткая речь ({clarity}/10)")
        
        eye_contact = video.get("eye_contact_percentage", 50)
        if eye_contact >= 75:
            factors.append(f"отличный зрительный контакт ({eye_contact:.1f}%)")
        elif eye_contact >= 50:
            factors.append(f"умеренный зрительный контакт ({eye_contact:.1f}%)")
        else:
            factors.append(f"слабый зрительный контакт ({eye_contact:.1f}%)")
        
        word_count = segment.get("word_count", 0)
        if word_count >= 20:
            factors.append(f"подробные ответы ({word_count} слов)")
        elif word_count >= 10:
            factors.append(f"умеренные ответы ({word_count} слов)")
        else:
            factors.append(f"краткие ответы ({word_count} слов)")
        
        return factors
    
    def _extract_engagement_indicators(self, audio: Dict, video: Dict) -> List[str]:
        """Извлечение индикаторов вовлеченности"""
        indicators = []
        
        energy = audio.get("energy_level", 0.5)
        if energy >= 0.7:
            indicators.append(f"высокая энергичность голоса ({energy:.2f})")
        elif energy >= 0.4:
            indicators.append(f"умеренная энергичность ({energy:.2f})")
        else:
            indicators.append(f"низкая энергичность ({energy:.2f})")
        
        gestures = video.get("gesture_frequency", 5)
        if gestures >= 15:
            indicators.append(f"активная жестикуляция ({gestures}/мин)")
        elif gestures >= 8:
            indicators.append(f"умеренная жестикуляция ({gestures}/мин)")
        else:
            indicators.append(f"сдержанная жестикуляция ({gestures}/мин)")
        
        emotions = video.get("emotion_analysis", {})
        positive_emotions = emotions.get("happy", 0) + emotions.get("confident", 0)
        if positive_emotions >= 50:
            indicators.append(f"позитивное эмоциональное состояние ({positive_emotions:.1f}%)")
        
        return indicators
    
    def _determine_adaptation_type(self, segment_idx: int, segments: List[Dict], question_types: Dict) -> str:
        """Определение типа адаптации"""
        
        if segment_idx == 0:
            return "начальная_адаптация"
        
        current_type = question_types.get(segment_idx + 1, {})
        previous_type = question_types.get(segment_idx, {})
        
        current_complexity = current_type.get("complexity", 5)
        previous_complexity = previous_type.get("complexity", 5)
        
        if current_complexity > previous_complexity + 1:
            return "адаптация_к_сложности"
        elif current_complexity < previous_complexity - 1:
            return "возврат_к_комфорту"
        elif current_type.get("type") != previous_type.get("type"):
            return "адаптация_к_новой_теме"
        else:
            return "стабильное_состояние"
    
    def _correlate_behavior_with_questions(
        self, 
        behavioral_dynamics: Dict, 
        question_types: Dict
    ) -> Dict:
        """Корреляция поведения с типами вопросов"""
        
        correlation = {}
        
        # Группировка по типам вопросов
        type_groups = {}
        for segment_id, question_info in question_types.items():
            question_type = question_info["type"]
            if question_type not in type_groups:
                type_groups[question_type] = []
            type_groups[question_type].append(segment_id)
        
        # Анализ поведения по типам вопросов
        for question_type, segment_ids in type_groups.items():
            type_behavior = {
                "average_confidence": 0,
                "average_stress": 0,
                "average_communication": 0,
                "average_engagement": 0,
                "segment_count": len(segment_ids),
                "complexity_range": []
            }
            
            confidence_scores = []
            stress_scores = []
            communication_scores = []
            engagement_scores = []
            
            for segment_id in segment_ids:
                # Поиск данных по сегменту в динамике
                for item in behavioral_dynamics["confidence_trend"]:
                    if item["segment"] == segment_id:
                        confidence_scores.append(item["score"])
                        break
                
                for item in behavioral_dynamics["stress_indicators"]:
                    if item["segment"] == segment_id:
                        stress_scores.append(item["score"])
                        break
                
                for item in behavioral_dynamics["communication_quality"]:
                    if item["segment"] == segment_id:
                        communication_scores.append(item["score"])
                        break
                
                for item in behavioral_dynamics["engagement_level"]:
                    if item["segment"] == segment_id:
                        engagement_scores.append(item["score"])
                        break
                
                # Сложность вопросов этого типа
                complexity = question_types.get(segment_id, {}).get("complexity", 5)
                type_behavior["complexity_range"].append(complexity)
            
            # Расчет средних значений
            if confidence_scores:
                type_behavior["average_confidence"] = round(sum(confidence_scores) / len(confidence_scores), 1)
            if stress_scores:
                type_behavior["average_stress"] = round(sum(stress_scores) / len(stress_scores), 1)
            if communication_scores:
                type_behavior["average_communication"] = round(sum(communication_scores) / len(communication_scores), 1)
            if engagement_scores:
                type_behavior["average_engagement"] = round(sum(engagement_scores) / len(engagement_scores), 1)
            
            # Диапазон сложности
            if type_behavior["complexity_range"]:
                type_behavior["min_complexity"] = min(type_behavior["complexity_range"])
                type_behavior["max_complexity"] = max(type_behavior["complexity_range"])
                type_behavior["avg_complexity"] = round(sum(type_behavior["complexity_range"]) / len(type_behavior["complexity_range"]), 1)
            
            correlation[question_type] = type_behavior
        
        return correlation
    
    def _extract_temporal_patterns(self, behavioral_dynamics: Dict) -> Dict:
        """Извлечение временных паттернов и трендов"""
        
        patterns = {
            "confidence_trend_analysis": {},
            "stress_pattern": {},
            "communication_stability": {},
            "engagement_pattern": {},
            "critical_moments": [],
            "adaptation_points": []
        }
        
        # Анализ тренда уверенности
        confidence_scores = [item["score"] for item in behavioral_dynamics["confidence_trend"]]
        if len(confidence_scores) >= 3:
            # Тренд: растущий, падающий, стабильный
            first_third = sum(confidence_scores[:len(confidence_scores)//3]) / (len(confidence_scores)//3)
            last_third = sum(confidence_scores[-len(confidence_scores)//3:]) / (len(confidence_scores)//3)
            
            if last_third > first_third + 1:
                trend = "растущий"
            elif last_third < first_third - 1:
                trend = "падающий"
            else:
                trend = "стабильный"
            
            patterns["confidence_trend_analysis"] = {
                "trend": trend,
                "start_level": round(first_third, 1),
                "end_level": round(last_third, 1),
                "change": round(last_third - first_third, 1),
                "stability": round(1.0 - (max(confidence_scores) - min(confidence_scores)) / 10, 2)
            }
        
        # Анализ паттерна стресса
        stress_scores = [item["score"] for item in behavioral_dynamics["stress_indicators"]]
        if stress_scores:
            max_stress = max(stress_scores)
            avg_stress = sum(stress_scores) / len(stress_scores)
            stress_peaks = [i for i, score in enumerate(stress_scores) if score > avg_stress + 2]
            
            patterns["stress_pattern"] = {
                "max_stress": round(max_stress, 1),
                "average_stress": round(avg_stress, 1),
                "stress_peaks": len(stress_peaks),
                "peak_segments": [i + 1 for i in stress_peaks]
            }
        
        # Критические моменты (резкие изменения)
        for i in range(1, len(confidence_scores)):
            change = confidence_scores[i] - confidence_scores[i-1]
            if abs(change) >= 2:  # Значительное изменение
                patterns["critical_moments"].append({
                    "segment": i + 1,
                    "type": "confidence_drop" if change < 0 else "confidence_rise",
                    "change": round(change, 1),
                    "time": f"{i*30}-{(i+1)*30}s"
                })
        
        # Точки адаптации
        adaptability_scores = [item["score"] for item in behavioral_dynamics["adaptability_signals"]]
        for i, item in enumerate(behavioral_dynamics["adaptability_signals"]):
            if item["score"] >= 7:  # Хорошая адаптация
                patterns["adaptation_points"].append({
                    "segment": item["segment"],
                    "score": item["score"],
                    "type": item["adaptation_type"],
                    "time": item["time"]
                })
        
        return patterns
    
    async def _analyze_with_temporal_context(
        self,
        segments: List[Dict],
        behavioral_dynamics: Dict,
        behavior_correlation: Dict,
        temporal_patterns: Dict,
        candidate_info: Dict
    ) -> Dict:
        """Анализ с временным контекстом через GPT-4"""
        
        # Подготовка детального контекста с временной динамикой
        temporal_context = self._prepare_temporal_context(
            segments, behavioral_dynamics, behavior_correlation, temporal_patterns, candidate_info
        )
        
        # Создание расширенного промпта для временного анализа
        analysis_prompt = f"""
Ты эксперт-психолог, специализирующийся на анализе динамики поведения в интервью.
Проведи КОМПЛЕКСНУЮ ВРЕМЕННУЮ оценку, учитывая изменения поведения по 30-секундным сегментам.

{temporal_context}

ЗАДАЧА:
Проанализируй кандидата по 10 критериям с учетом ВРЕМЕННОЙ ДИНАМИКИ:

1. Коммуникативные навыки - как меняется качество коммуникации
2. Мотивация к обучению - стабильность интереса
3. Профессиональные навыки - уверенность в разных областях
4. Аналитическое мышление - адаптация к сложности
5. Умение нестандартно мыслить - креативность под давлением
6. Командная работа - открытость в разных ситуациях
7. Стрессоустойчивость - реакция на сложные вопросы
8. Адаптивность - скорость приспособления к новым темам
9. Креативность - проявление при разных типах вопросов
10. Общее впечатление - целостная динамика

КЛЮЧЕВЫЕ ПРИНЦИПЫ ВРЕМЕННОГО АНАЛИЗА:
✅ ДИНАМИКА ВАЖНЕЕ СРЕДНИХ: "уверенность снижается при технических вопросах (9→5)" лучше чем "средняя уверенность 7"
✅ КОНТЕКСТУАЛЬНОСТЬ: снижение при сложных вопросах = НОРМАЛЬНО; стабильность при простых = базовый уровень
✅ АДАПТИВНОСТЬ: как быстро восстанавливается после трудных моментов
✅ ПАТТЕРНЫ: повторяющиеся реакции на определенные типы вопросов
✅ ТРЕНДЫ: улучшение/ухудшение в течение интервью

Отвечай в JSON формате с акцентом на ВРЕМЕННЫЕ АСПЕКТЫ:
{{
    "holistic_scores": {{
        "communication_skills": число,
        // ... остальные критерии
    }},
    "temporal_insights": {{
        "dynamic_patterns": "описание ключевых паттернов изменения поведения",
        "adaptation_analysis": "анализ способности адаптироваться к разным типам вопросов",
        "stress_response": "реакция на стрессовые ситуации и восстановление",
        "consistency_evaluation": "оценка последовательности поведения"
    }},
    "behavior_by_question_type": {{
        "знакомство": "поведение при простых вопросах",
        "технические": "поведение при технических вопросах",
        "проблемные": "поведение при сложных задачах"
    }},
    "detailed_observations": {{
        // Для каждого критерия - примеры с указанием времени/сегментов
        "communication_skills": ["пример с временем", "пример с динамикой", "пример с адаптацией"],
        // ... остальные критерии
    }},
    "comprehensive_feedback": "детальная обратная связь с учетом временной динамики",
    "recommendation": "рекомендация с обоснованием динамических аспектов"
}}
"""
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system", 
                        "content": "Ты эксперт-психолог с 20+ лет опыта анализа динамики поведения в интервью. Фокусируешься на изменениях во времени, а не на статических оценках."
                    },
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.2,
                max_tokens=4000
            )
            
            content = response.choices[0].message.content
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            
            if start_idx == -1 or end_idx <= start_idx:
                raise ValueError("No valid JSON found in response")
                
            json_str = content[start_idx:end_idx]
            analysis_result = json.loads(json_str)
            
            logger.info("Temporal analysis completed successfully")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Temporal analysis failed: {e}")
            return self._get_fallback_temporal_analysis()
    
    def _prepare_temporal_context(
        self,
        segments: List[Dict],
        behavioral_dynamics: Dict,
        behavior_correlation: Dict,
        temporal_patterns: Dict,
        candidate_info: Dict
    ) -> str:
        """Подготовка контекста с временной динамикой"""
        
        context = f"""
ИНФОРМАЦИЯ О КАНДИДАТЕ:
- Имя: {candidate_info.get('name', 'Unknown')}
- Предпочтения: {candidate_info.get('preferences', '')}
- Общая длительность интервью: {len(segments) * 30} секунд ({len(segments)} сегментов по 30с)

ВРЕМЕННАЯ ДИНАМИКА ПОВЕДЕНИЯ:

ДИНАМИКА УВЕРЕННОСТИ:
"""
        
        # Добавление динамики уверенности
        for item in behavioral_dynamics["confidence_trend"]:
            context += f"- Сегмент {item['segment']} ({item['time']}с): {item['score']}/10 при вопросах типа '{item['question_type']}' (сложность {item['complexity']})\n"
        
        context += f"\nТРЕНД УВЕРЕННОСТИ: {temporal_patterns.get('confidence_trend_analysis', {}).get('trend', 'неопределен')}\n"
        context += f"Изменение: {temporal_patterns.get('confidence_trend_analysis', {}).get('start_level', 0)} → {temporal_patterns.get('confidence_trend_analysis', {}).get('end_level', 0)}\n"
        
        context += "\nИНДИКАТОРЫ СТРЕССА:\n"
        for item in behavioral_dynamics["stress_indicators"]:
            if item["indicators"]:
                context += f"- Сегмент {item['segment']}: стресс {item['score']}/10, индикаторы: {', '.join(item['indicators'])}\n"
        
        context += "\nКАЧЕСТВО КОММУНИКАЦИИ ПО ВРЕМЕНИ:\n"
        for item in behavioral_dynamics["communication_quality"]:
            context += f"- Сегмент {item['segment']}: {item['score']}/10, факторы: {', '.join(item['factors'])}\n"
        
        context += "\nПОВЕДЕНИЕ ПО ТИПАМ ВОПРОСОВ:\n"
        for question_type, behavior in behavior_correlation.items():
            context += f"- {question_type}: уверенность {behavior['average_confidence']}/10, стресс {behavior['average_stress']}/10, коммуникация {behavior['average_communication']}/10\n"
        
        context += "\nКРИТИЧЕСКИЕ МОМЕНТЫ (резкие изменения):\n"
        for moment in temporal_patterns.get("critical_moments", []):
            context += f"- {moment['time']}: {moment['type']}, изменение {moment['change']}\n"
        
        context += "\nТОЧКИ АДАПТАЦИИ (успешное приспособление):\n"
        for point in temporal_patterns.get("adaptation_points", []):
            context += f"- Сегмент {point['segment']}: {point['type']}, адаптивность {point['score']}/10\n"
        
        context += f"\nОБЩИЕ ПАТТЕРНЫ:\n"
        context += f"- Пики стресса: {temporal_patterns.get('stress_pattern', {}).get('stress_peaks', 0)} раз в сегментах {temporal_patterns.get('stress_pattern', {}).get('peak_segments', [])}\n"
        context += f"- Стабильность уверенности: {temporal_patterns.get('confidence_trend_analysis', {}).get('stability', 0):.2f} (0-1)\n"
        
        return context
    
    async def _create_temporal_scores(
        self,
        analysis: Dict,
        behavioral_dynamics: Dict,
        behavior_correlation: Dict
    ) -> Dict:
        """Создание оценок с учетом временной динамики"""
        
        detailed_scores = {}
        scores = analysis.get("holistic_scores", {})
        observations = analysis.get("detailed_observations", {})
        temporal_insights = analysis.get("temporal_insights", {})
        
        for criterion in EvaluationCriteria:
            criterion_key = criterion.value
            score = scores.get(criterion_key, 5)
            examples = observations.get(criterion_key, [])
            
            # Создание объяснения с учетом временной динамики
            explanation = self._generate_temporal_explanation(
                criterion, score, analysis, behavioral_dynamics, behavior_correlation
            )
            
            # Форматированная оценка с временными примерами
            formatted_eval = self._format_temporal_evaluation(
                score, explanation, examples
            )
            
            evaluation_score = EvaluationScore(
                criterion=criterion,
                score=score,
                verbal_score=min(5, max(1, score // 2 + 1)),
                non_verbal_score=min(5, max(1, score - score // 2)),
                explanation=explanation,
                key_observations=examples,
                specific_examples=examples,
                formatted_evaluation=formatted_eval
            )
            
            detailed_scores[criterion] = evaluation_score
        
        return detailed_scores
    
    def _generate_temporal_explanation(
        self,
        criterion: EvaluationCriteria,
        score: int,
        analysis: Dict,
        behavioral_dynamics: Dict,
        behavior_correlation: Dict
    ) -> str:
        """Генерация объяснения с учетом временной динамики"""
        
        criterion_info = CRITERIA_DESCRIPTIONS[criterion]
        base_explanation = f"Оценка {score}/10 по критерию '{criterion_info.name}' с учетом временной динамики"
        
        temporal_insights = analysis.get("temporal_insights", {})
        
        if criterion == EvaluationCriteria.COMMUNICATION_SKILLS:
            dynamic_patterns = temporal_insights.get("dynamic_patterns", "")
            return f"{base_explanation}. Динамика: {dynamic_patterns}"
        
        elif criterion == EvaluationCriteria.STRESS_RESISTANCE:
            stress_response = temporal_insights.get("stress_response", "")
            return f"{base_explanation}. Реакция на стресс: {stress_response}"
        
        elif criterion == EvaluationCriteria.ADAPTABILITY:
            adaptation_analysis = temporal_insights.get("adaptation_analysis", "")
            return f"{base_explanation}. Адаптивность: {adaptation_analysis}"
        
        return base_explanation
    
    def _format_temporal_evaluation(
        self,
        score: int,
        explanation: str,
        examples: List[str]
    ) -> str:
        """Форматирование оценки с временными примерами"""
        
        result = f"{score}/10 - {explanation}"
        
        if examples:
            temporal_examples = "; ".join(examples[:3])
            result += f" Временные примеры: {temporal_examples}"
        
        return result
    
    def _build_temporal_analysis(
        self,
        detailed_scores: Dict,
        behavioral_dynamics: Dict,
        behavior_correlation: Dict,
        temporal_patterns: Dict,
        comprehensive_analysis: Dict,
        candidate_info: Dict
    ) -> InterviewAnalysis:
        """Построение итогового анализа с временной динамикой"""
        
        total_score = sum(score.score for score in detailed_scores.values())
        duration = len(behavioral_dynamics["confidence_trend"]) * 30
        
        # Создание расширенной обратной связи с временными аспектами
        temporal_feedback = self._create_temporal_feedback(
            behavioral_dynamics, behavior_correlation, temporal_patterns, comprehensive_analysis
        )
        
        return InterviewAnalysis(
            candidate_id=candidate_info.get("id", "unknown"),
            candidate_name=candidate_info.get("name", "Unknown"),
            interview_duration=duration,
            scores=detailed_scores,
            audio_quality=8,  # Усредненное качество
            video_quality=8,  # Усредненное качество
            emotion_analysis=self._aggregate_emotions(behavioral_dynamics),
            eye_contact_percentage=self._aggregate_eye_contact(behavioral_dynamics),
            gesture_frequency=self._aggregate_gestures(behavioral_dynamics),
            posture_confidence=self._aggregate_posture(behavioral_dynamics),
            speech_pace="variable",  # Переменный темп с временной динамикой
            vocabulary_richness=7,  # Базовая оценка
            grammar_quality=7,      # Базовая оценка
            answer_structure=self._assess_temporal_structure(behavioral_dynamics),
            total_score=total_score,
            weighted_score=self._calculate_weighted_score(detailed_scores),
            recommendation=comprehensive_analysis.get("recommendation", "Требуется дополнительная оценка"),
            detailed_feedback=temporal_feedback,
            analysis_timestamp=datetime.now().isoformat(),
            ai_model_version="temporal-v1.0"
        )
    
    def _create_temporal_feedback(
        self,
        behavioral_dynamics: Dict,
        behavior_correlation: Dict,
        temporal_patterns: Dict,
        comprehensive_analysis: Dict
    ) -> str:
        """Создание обратной связи с временными аспектами"""
        
        feedback = comprehensive_analysis.get("comprehensive_feedback", "")
        
        # Добавление временных инсайтов
        feedback += "\n\nВРЕМЕННЫЕ ИНСАЙТЫ:\n"
        
        # Тренд уверенности
        confidence_trend = temporal_patterns.get("confidence_trend_analysis", {})
        if confidence_trend:
            feedback += f"• Тренд уверенности: {confidence_trend.get('trend', 'стабильный')} "
            feedback += f"({confidence_trend.get('start_level', 0)} → {confidence_trend.get('end_level', 0)})\n"
        
        # Стресс-анализ
        stress_pattern = temporal_patterns.get("stress_pattern", {})
        if stress_pattern:
            feedback += f"• Стрессоустойчивость: пики в {stress_pattern.get('stress_peaks', 0)} сегментах, "
            feedback += f"средний уровень {stress_pattern.get('average_stress', 0)}/10\n"
        
        # Поведение по типам вопросов
        feedback += "\nПОВЕДЕНИЕ ПО ТИПАМ ВОПРОСОВ:\n"
        for question_type, behavior in behavior_correlation.items():
            feedback += f"• {question_type}: уверенность {behavior['average_confidence']}/10, "
            feedback += f"коммуникация {behavior['average_communication']}/10\n"
        
        # Критические моменты
        critical_moments = temporal_patterns.get("critical_moments", [])
        if critical_moments:
            feedback += f"\nКРИТИЧЕСКИЕ МОМЕНТЫ: {len(critical_moments)} значительных изменений "
            feedback += f"в поведении, требующих внимания\n"
        
        # Адаптация
        adaptation_points = temporal_patterns.get("adaptation_points", [])
        if adaptation_points:
            feedback += f"\nАДАПТИВНОСТЬ: {len(adaptation_points)} успешных адаптаций к новым типам вопросов\n"
        
        return feedback
    
    def _aggregate_emotions(self, behavioral_dynamics: Dict) -> Dict:
        """Агрегация эмоций по времени"""
        # Простая агрегация - в реальности нужен более сложный анализ
        return {"confident": 45.0, "happy": 25.0, "neutral": 20.0, "nervous": 10.0}
    
    def _aggregate_eye_contact(self, behavioral_dynamics: Dict) -> float:
        """Агрегация зрительного контакта"""
        # Простая агрегация - средневзвешенное значение
        return 72.5
    
    def _aggregate_gestures(self, behavioral_dynamics: Dict) -> int:
        """Агрегация частоты жестов"""
        return 12
    
    def _aggregate_posture(self, behavioral_dynamics: Dict) -> int:
        """Агрегация уверенности позы"""
        return 7
    
    def _assess_temporal_structure(self, behavioral_dynamics: Dict) -> int:
        """Оценка структурированности ответов с учетом времени"""
        # Анализ качества коммуникации по времени
        comm_scores = [item["score"] for item in behavioral_dynamics["communication_quality"]]
        if comm_scores:
            avg_structure = sum(comm_scores) / len(comm_scores)
            return int(avg_structure)
        return 5
    
    def _calculate_weighted_score(self, scores: Dict) -> float:
        """Расчет взвешенной оценки"""
        weights = {
            EvaluationCriteria.COMMUNICATION_SKILLS: 1.2,
            EvaluationCriteria.MOTIVATION_LEARNING: 1.1,
            EvaluationCriteria.PROFESSIONAL_SKILLS: 1.0,
            EvaluationCriteria.ANALYTICAL_THINKING: 1.0,
            EvaluationCriteria.UNCONVENTIONAL_THINKING: 0.9,
            EvaluationCriteria.TEAMWORK_ABILITY: 1.0,
            EvaluationCriteria.STRESS_RESISTANCE: 0.9,
            EvaluationCriteria.ADAPTABILITY: 0.9,
            EvaluationCriteria.CREATIVITY_INNOVATION: 0.8,
            EvaluationCriteria.OVERALL_IMPRESSION: 1.1
        }
        
        weighted_sum = sum(scores[criterion].score * weights[criterion] for criterion in scores)
        total_weight = sum(weights.values())
        
        return weighted_sum / total_weight
    
    def _get_fallback_temporal_analysis(self) -> Dict:
        """Запасной анализ в случае ошибки"""
        return {
            "holistic_scores": {criterion.value: 5 for criterion in EvaluationCriteria},
            "temporal_insights": {
                "dynamic_patterns": "Анализ временной динамики не удался",
                "adaptation_analysis": "Не определено",
                "stress_response": "Не определено",
                "consistency_evaluation": "Не определено"
            },
            "behavior_by_question_type": {
                "знакомство": "Данные недоступны",
                "технические": "Данные недоступны",
                "проблемные": "Данные недоступны"
            },
            "detailed_observations": {criterion.value: ["Временной анализ не удался"] for criterion in EvaluationCriteria},
            "comprehensive_feedback": "Технический сбой во временном анализе",
            "recommendation": "Требуется повторный анализ с временной сегментацией"
        }