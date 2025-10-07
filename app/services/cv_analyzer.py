"""
Сервис анализа CV кандидата
Извлекает текст из CV и анализирует его с помощью GPT
"""

import os
import aiohttp
import logging
from typing import Dict, Any, Optional
import openai
from io import BytesIO
import PyPDF2
import docx
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class CVAnalyzer:
    """Анализатор CV кандидата"""
    
    def __init__(self, openai_client):
        self.openai_client = openai_client
        
    async def analyze_cv(self, cv_url: str, candidate_name: str) -> Dict[str, Any]:
        """Анализ CV кандидата"""
        if not cv_url:
            logger.info("No CV URL provided, skipping CV analysis")
            return {
                "cv_text": "",
                "cv_analysis": "CV не предоставлено",
                "cv_score": 5,  # Нейтральная оценка
                "relevant_experience": "",
                "technical_skills": [],
                "education": "",
                "projects": [],
                "languages": [],
                "cv_quality": "not_provided"
            }
        
        try:
            # Загрузка и извлечение текста CV
            cv_text = await self._extract_cv_text(cv_url)
            
            if not cv_text:
                logger.warning(f"Failed to extract text from CV: {cv_url}")
                return {
                    "cv_text": "",
                    "cv_analysis": "Не удалось извлечь текст из CV",
                    "cv_score": 3,
                    "relevant_experience": "",
                    "technical_skills": [],
                    "education": "",
                    "projects": [],
                    "languages": [],
                    "cv_quality": "extraction_failed"
                }
            
            # Анализ CV с помощью GPT
            analysis_result = await self._analyze_cv_with_gpt(cv_text, candidate_name)
            
            analysis_result["cv_text"] = cv_text[:2000]  # Ограничиваем длину
            
            logger.info(f"CV analysis completed for {candidate_name}")
            return analysis_result
            
        except Exception as e:
            logger.error(f"CV analysis failed for {candidate_name}: {e}")
            return {
                "cv_text": "",
                "cv_analysis": f"Ошибка анализа CV: {str(e)}",
                "cv_score": 1,
                "relevant_experience": "",
                "technical_skills": [],
                "education": "",
                "projects": [],
                "languages": [],
                "cv_quality": "analysis_error"
            }
    
    async def _extract_cv_text(self, cv_url: str) -> str:
        """Извлечение текста из CV (поддерживает PDF, DOCX, TXT)"""
        try:
            # Загрузка файла
            async with aiohttp.ClientSession() as session:
                async with session.get(cv_url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to download CV from {cv_url}: {response.status}")
                        return ""
                    
                    content = await response.read()
            
            # Определение типа файла
            parsed_url = urlparse(cv_url)
            file_extension = parsed_url.path.lower().split('.')[-1]
            
            if file_extension == 'pdf':
                return self._extract_pdf_text(content)
            elif file_extension in ['docx', 'doc']:
                return self._extract_docx_text(content)
            elif file_extension == 'txt':
                return content.decode('utf-8', errors='ignore')
            else:
                # Попробуем как текст
                try:
                    return content.decode('utf-8', errors='ignore')
                except:
                    logger.error(f"Unsupported file format: {file_extension}")
                    return ""
                    
        except Exception as e:
            logger.error(f"Error extracting CV text: {e}")
            return ""
    
    def _extract_pdf_text(self, content: bytes) -> str:
        """Извлечение текста из PDF"""
        try:
            pdf_file = BytesIO(content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\\n"
            
            return text.strip()
            
        except Exception as e:
            logger.error(f"Error extracting PDF text: {e}")
            return ""
    
    def _extract_docx_text(self, content: bytes) -> str:
        """Извлечение текста из DOCX"""
        try:
            doc = docx.Document(BytesIO(content))
            text = ""
            
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\\n"
            
            return text.strip()
            
        except Exception as e:
            logger.error(f"Error extracting DOCX text: {e}")
            return ""
    
    async def _analyze_cv_with_gpt(self, cv_text: str, candidate_name: str) -> Dict[str, Any]:
        """Анализ CV с помощью GPT"""
        
        analysis_prompt = f"""
        Ты HR-эксперт, специализирующийся на анализе резюме IT-кандидатов.
        
        Проанализируй CV кандидата {candidate_name} и предоставь детальную оценку:
        
        CV ТЕКСТ:
        {cv_text}
        
        ЗАДАЧА АНАЛИЗА:
        1. Извлеки ключевую информацию о кандидате
        2. Оцени релевантность опыта для IT-позиций
        3. Проанализируй технические навыки
        4. Оцени качество и структуру CV
        5. Дай общую оценку от 1 до 10
        
        ФОРМАТИРОВАНИЕ ОТВЕТА (JSON):
        {{
            "cv_analysis": "Детальный анализ CV с конкретными примерами и рекомендациями",
            "cv_score": 8,
            "relevant_experience": "Описание релевантного опыта работы",
            "technical_skills": ["Python", "JavaScript", "React", "SQL"],
            "education": "Информация об образовании",
            "projects": ["Описание проекта 1", "Описание проекта 2"],
            "languages": ["Русский (родной)", "Английский (B2)"],
            "cv_quality": "good",
            "strengths": ["Сильная сторона 1", "Сильная сторона 2"],
            "weaknesses": ["Слабая сторона 1", "Слабая сторона 2"],
            "recommendations": "Рекомендации по улучшению CV"
        }}
        
        КРИТЕРИИ ОЦЕНКИ:
        - 9-10: Выдающееся CV с богатым опытом и проектами
        - 7-8: Хорошее CV с релевантным опытом
        - 5-6: Среднее CV с базовыми навыками
        - 3-4: Слабое CV с ограниченным опытом
        - 1-2: Очень слабое CV или студент без опыта
        
        ВАЖНО: 
        - Фокусируйся на IT-навыках и проектах
        - Учитывай качество оформления CV
        - Отмечай конкретные достижения и метрики
        - Анализируй прогрессию карьеры
        """
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # Используем более дешевую модель для анализа CV
                messages=[
                    {"role": "system", "content": "Ты профессиональный HR-аналитик, специализирующийся на IT-резюме."},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.3,
                max_tokens=1500
            )
            
            analysis_text = response.choices[0].message.content
            
            # Парсинг JSON ответа
            import json
            try:
                analysis_json = json.loads(analysis_text)
                return analysis_json
            except json.JSONDecodeError:
                # Если JSON не удалось распарсить, возвращаем текстовый анализ
                return {
                    "cv_analysis": analysis_text,
                    "cv_score": 5,
                    "relevant_experience": "Не удалось извлечь структурированные данные",
                    "technical_skills": [],
                    "education": "",
                    "projects": [],
                    "languages": [],
                    "cv_quality": "analysis_partial",
                    "strengths": [],
                    "weaknesses": [],
                    "recommendations": "Необходим ручной анализ"
                }
            
        except Exception as e:
            logger.error(f"GPT CV analysis failed: {e}")
            return {
                "cv_analysis": f"Ошибка анализа GPT: {str(e)}",
                "cv_score": 3,
                "relevant_experience": "",
                "technical_skills": [],
                "education": "",
                "projects": [],
                "languages": [],
                "cv_quality": "gpt_error",
                "strengths": [],
                "weaknesses": [],
                "recommendations": ""
            }