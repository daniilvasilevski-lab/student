"""
Сервис анализа вопросов интервью
Загружает вопросы и анализирует их структуру и типы для временного анализа
"""

import os
import aiohttp
import logging
from typing import Dict, Any, List, Optional
import openai
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class QuestionsAnalyzer:
    """Анализатор вопросов интервью"""
    
    def __init__(self, openai_client):
        self.openai_client = openai_client
        
    async def analyze_questions(self, questions_url: str, candidate_name: str) -> Dict[str, Any]:
        """Анализ вопросов интервью"""
        if not questions_url:
            logger.info("No questions URL provided, using default question types")
            return {
                "questions_text": "",
                "questions_analysis": "Вопросы не предоставлены, используется автоматическая классификация",
                "question_types": [],
                "complexity_levels": [],
                "interview_structure": "auto_detected",
                "total_questions": 0,
                "expected_duration": 0
            }
        
        try:
            # Загрузка текста вопросов
            questions_text = await self._extract_questions_text(questions_url)
            
            if not questions_text:
                logger.warning(f"Failed to extract questions from: {questions_url}")
                return {
                    "questions_text": "",
                    "questions_analysis": "Не удалось загрузить вопросы",
                    "question_types": [],
                    "complexity_levels": [],
                    "interview_structure": "extraction_failed",
                    "total_questions": 0,
                    "expected_duration": 0
                }
            
            # Анализ вопросов с помощью GPT
            analysis_result = await self._analyze_questions_with_gpt(questions_text, candidate_name)
            
            analysis_result["questions_text"] = questions_text[:1000]  # Ограничиваем длину
            
            logger.info(f"Questions analysis completed for {candidate_name}")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Questions analysis failed for {candidate_name}: {e}")
            return {
                "questions_text": "",
                "questions_analysis": f"Ошибка анализа вопросов: {str(e)}",
                "question_types": [],
                "complexity_levels": [],
                "interview_structure": "analysis_error",
                "total_questions": 0,
                "expected_duration": 0
            }
    
    async def _extract_questions_text(self, questions_url: str) -> str:
        """Извлечение текста вопросов (поддерживает текстовые файлы, простые форматы)"""
        try:
            # Загрузка файла
            async with aiohttp.ClientSession() as session:
                async with session.get(questions_url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to download questions from {questions_url}: {response.status}")
                        return ""
                    
                    content = await response.read()
            
            # Определение типа файла
            parsed_url = urlparse(questions_url)
            file_extension = parsed_url.path.lower().split('.')[-1]
            
            if file_extension in ['txt', 'md', 'rtf']:
                return content.decode('utf-8', errors='ignore')
            else:
                # Попробуем как текст
                try:
                    return content.decode('utf-8', errors='ignore')
                except:
                    logger.error(f"Unsupported questions file format: {file_extension}")
                    return ""
                    
        except Exception as e:
            logger.error(f"Error extracting questions text: {e}")
            return ""
    
    async def _analyze_questions_with_gpt(self, questions_text: str, candidate_name: str) -> Dict[str, Any]:
        """Анализ вопросов с помощью GPT"""
        
        analysis_prompt = f"""
        Ты эксперт по проведению интервью, специализирующийся на анализе структуры вопросов.
        
        Проанализируй список вопросов для интервью кандидата {candidate_name}:
        
        ВОПРОСЫ ИНТЕРВЬЮ:
        {questions_text}
        
        ЗАДАЧА АНАЛИЗА:
        1. Классифицируй каждый вопрос по типам
        2. Определи уровень сложности каждого вопроса
        3. Проанализируй структуру интервью
        4. Оцени ожидаемую длительность
        5. Дай рекомендации по проведению
        
        ТИПЫ ВОПРОСОВ:
        - "знакомство" - представление, общие вопросы о себе
        - "опыт" - обсуждение опыта работы, проектов
        - "технические" - профессиональные навыки, технологии
        - "поведенческие" - вопросы о поведении в ситуациях
        - "проблемные" - сложные задачи, алгоритмы, кейсы
        - "мотивация" - цели, интересы, планы
        - "личные" - личные качества, хобби, ценности
        
        УРОВНИ СЛОЖНОСТИ:
        - 1-3: Простые вопросы (знакомство, базовые)
        - 4-6: Средние вопросы (опыт, технические)
        - 7-10: Сложные вопросы (проблемные, алгоритмы)
        
        ФОРМАТИРОВАНИЕ ОТВЕТА (JSON):
        {{
            "questions_analysis": "Детальный анализ структуры вопросов и рекомендации",
            "question_types": [
                {{"question": "Вопрос 1", "type": "знакомство", "complexity": 2}},
                {{"question": "Вопрос 2", "type": "технические", "complexity": 6}},
                {{"question": "Вопрос 3", "type": "проблемные", "complexity": 9}}
            ],
            "complexity_levels": [2, 6, 9],
            "interview_structure": "progressive",
            "total_questions": 15,
            "expected_duration": 45,
            "type_distribution": {{
                "знакомство": 3,
                "опыт": 4,
                "технические": 5,
                "поведенческие": 2,
                "проблемные": 1
            }},
            "recommendations": "Рекомендации по проведению интервью"
        }}
        
        СТРУКТУРЫ ИНТЕРВЬЮ:
        - "progressive" - постепенное усложнение
        - "mixed" - смешанная структура
        - "technical_focus" - фокус на технических вопросах
        - "behavioral_focus" - фокус на поведенческих вопросах
        - "unstructured" - без четкой структуры
        
        ВАЖНО:
        - Анализируй реальную сложность вопросов
        - Учитывай логику построения интервью
        - Оценивай время на каждый тип вопросов
        - Давай практические рекомендации
        """
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # Используем дешевую модель для анализа вопросов
                messages=[
                    {"role": "system", "content": "Ты эксперт по структуре интервью и классификации вопросов."},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.2,
                max_tokens=1200
            )
            
            analysis_text = response.choices[0].message.content
            
            # Парсинг JSON ответа
            import json
            try:
                analysis_json = json.loads(analysis_text)
                return analysis_json
            except json.JSONDecodeError:
                # Если JSON не удалось распарсить, возвращаем базовый анализ
                logger.warning("Failed to parse questions analysis JSON")
                return {
                    "questions_analysis": analysis_text,
                    "question_types": [],
                    "complexity_levels": [],
                    "interview_structure": "analysis_partial",
                    "total_questions": 0,
                    "expected_duration": 30,  # Предполагаем 30 минут
                    "type_distribution": {},
                    "recommendations": "Необходим ручной анализ вопросов"
                }
            
        except Exception as e:
            logger.error(f"GPT questions analysis failed: {e}")
            return {
                "questions_analysis": f"Ошибка анализа GPT: {str(e)}",
                "question_types": [],
                "complexity_levels": [],
                "interview_structure": "gpt_error",
                "total_questions": 0,
                "expected_duration": 0,
                "type_distribution": {},
                "recommendations": ""
            }
    
    def get_question_timing_map(self, question_types: List[Dict], interview_duration: int) -> Dict[str, Any]:
        """Создание карты соответствия времени интервью и типов вопросов"""
        if not question_types or interview_duration <= 0:
            return {
                "segments": [],
                "question_timeline": [],
                "accuracy": "low"
            }
        
        try:
            # Расчет времени на каждый вопрос
            total_questions = len(question_types)
            avg_time_per_question = interview_duration / total_questions if total_questions > 0 else 60
            
            # Создание временной линии вопросов
            timeline = []
            current_time = 0
            
            for i, question_data in enumerate(question_types):
                question = question_data.get("question", f"Вопрос {i+1}")
                question_type = question_data.get("type", "unknown")
                complexity = question_data.get("complexity", 5)
                
                # Время на вопрос зависит от сложности
                question_duration = avg_time_per_question * (0.5 + complexity * 0.1)
                question_duration = max(30, min(question_duration, 300))  # От 30 секунд до 5 минут
                
                timeline.append({
                    "question": question,
                    "type": question_type,
                    "complexity": complexity,
                    "start_time": current_time,
                    "end_time": current_time + question_duration,
                    "duration": question_duration
                })
                
                current_time += question_duration
            
            # Создание 30-секундных сегментов
            segments = []
            segment_id = 1
            segment_time = 0
            
            while segment_time < interview_duration:
                segment_end = min(segment_time + 30, interview_duration)
                
                # Найти активные вопросы в этом сегменте
                active_questions = []
                for q in timeline:
                    if (q["start_time"] <= segment_time < q["end_time"] or 
                        q["start_time"] < segment_end <= q["end_time"] or
                        (segment_time <= q["start_time"] and q["end_time"] <= segment_end)):
                        active_questions.append(q)
                
                # Определить доминирующий тип вопроса
                if active_questions:
                    # Берем вопрос с наибольшим перекрытием
                    main_question = max(active_questions, 
                                      key=lambda q: min(q["end_time"], segment_end) - max(q["start_time"], segment_time))
                    segment_type = main_question["type"]
                    segment_complexity = main_question["complexity"]
                else:
                    segment_type = "unknown"
                    segment_complexity = 5
                
                segments.append({
                    "segment_id": segment_id,
                    "start_time": segment_time,
                    "end_time": segment_end,
                    "question_type": segment_type,
                    "complexity": segment_complexity,
                    "active_questions": [q["question"] for q in active_questions]
                })
                
                segment_id += 1
                segment_time += 30
            
            return {
                "segments": segments,
                "question_timeline": timeline,
                "accuracy": "high",
                "total_duration": current_time,
                "questions_coverage": len([q for q in timeline if q["duration"] > 0])
            }
            
        except Exception as e:
            logger.error(f"Error creating question timing map: {e}")
            return {
                "segments": [],
                "question_timeline": [],
                "accuracy": "error"
            }