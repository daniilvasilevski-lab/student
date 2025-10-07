"""
Сервис для записи результатов анализа в отдельную Google таблицу с поддержкой языков
"""

import logging
from typing import Dict, List, Any, Optional
import gspread
from google.oauth2.service_account import Credentials
import os
from datetime import datetime
import re

from ..models.evaluation_criteria import InterviewAnalysis, EvaluationCriteria, CRITERIA_DESCRIPTIONS

logger = logging.getLogger(__name__)


class ResultsSheetsService:
    """Сервис для работы с Google Sheets результатов анализа с мультиязычной поддержкой"""
    
    def __init__(self):
        self.gc = None
        self.sheets = {}  # Словарь листов для разных языков
        self.results_spreadsheet_id = os.getenv("RESULTS_SHEET_ID")
        self.language_sheets = {
            'ru': 'Results_ru',
            'en': 'Results_en', 
            'pl': 'Results_pl'
        }
        self._initialize_service()
        
    # Определения заголовков для разных языков
    @property
    def headers_by_language(self):
        return {
            'ru': [
                "Имя", "Email", "Телефон",
                "1. Коммуникативные навыки", "2. Мотивация к обучению", "3. Профессиональные навыки",
                "4. Аналитическое мышление", "5. Нестандартное мышление", "6. Командная работа",
                "7. Стрессоустойчивость", "8. Адаптивность", "9. Креативность",
                "10. Общее впечатление", "Финальная оценка", "Рекомендация"
            ],
            'en': [
                "Name", "Email", "Phone", 
                "1. Communication Skills", "2. Motivation & Learning", "3. Professional Skills",
                "4. Analytical Thinking", "5. Unconventional Thinking", "6. Teamwork Ability", 
                "7. Stress Resistance", "8. Adaptability", "9. Creativity & Innovation",
                "10. Overall Impression", "Final Score", "Recommendation"
            ],
            'pl': [
                "Imię", "Email", "Telefon",
                "1. Umiejętności komunikacyjne", "2. Motywacja do nauki", "3. Umiejętności zawodowe",
                "4. Myślenie analityczne", "5. Myślenie nieszablonowe", "6. Praca zespołowa",
                "7. Odporność na stres", "8. Adaptacyjność", "9. Kreatywność",
                "10. Ogólne wrażenie", "Ocena końcowa", "Rekomendacja"
            ]
        }
    
    def _initialize_service(self):
        """Инициализация сервиса Google Sheets"""
        try:
            # Получение credentials из переменных окружения
            creds_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY")
            if not creds_path or not os.path.exists(creds_path):
                logger.warning("Google Sheets credentials not found")
                return
            
            # Создание credentials из файла
            scope = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            
            credentials = Credentials.from_service_account_file(creds_path, scopes=scope)
            self.gc = gspread.authorize(credentials)
            
            # Подключение к таблице результатов и инициализация языковых листов
            if self.results_spreadsheet_id:
                self.spreadsheet = self.gc.open_by_key(self.results_spreadsheet_id)
                self._initialize_language_sheets()
            
            logger.info("Results Google Sheets service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Results Google Sheets service: {e}")
            self.gc = None
            self.spreadsheet = None
    
    def _initialize_language_sheets(self):
        """Инициализация листов для разных языков"""
        for lang_code, sheet_name in self.language_sheets.items():
            try:
                # Попытка получить существующий лист
                sheet = self.spreadsheet.worksheet(sheet_name)
                self.sheets[lang_code] = sheet
                logger.info(f"Connected to existing {sheet_name} sheet")
                
                # Проверка заголовков
                self._ensure_headers_exist(lang_code)
                
            except gspread.WorksheetNotFound:
                # Создание нового листа
                sheet = self.spreadsheet.add_worksheet(
                    title=sheet_name,
                    rows=1000,
                    cols=20
                )
                self.sheets[lang_code] = sheet
                self._setup_headers_for_language(lang_code)
                logger.info(f"Created new {sheet_name} sheet")
                
            except Exception as e:
                logger.error(f"Failed to initialize {sheet_name}: {e}")
    
    def _ensure_headers_exist(self, language: str):
        """Проверка и создание заголовков если их нет"""
        if language not in self.sheets:
            return
            
        try:
            sheet = self.sheets[language]
            headers = sheet.row_values(1)
            
            # Если заголовков нет или они неполные, создаем их
            expected_headers = self.headers_by_language[language]
            if not headers or len(headers) < len(expected_headers):
                self._setup_headers_for_language(language)
                
        except Exception as e:
            logger.error(f"Failed to check headers for {language}: {e}")
    
    def _setup_headers_for_language(self, language: str):
        """Настройка заголовков для конкретного языка"""
        if language not in self.sheets or language not in self.headers_by_language:
            return
            
        try:
            sheet = self.sheets[language]
            headers = self.headers_by_language[language]
            
            # Очистка первой строки и установка заголовков
            sheet.clear()
            sheet.append_row(headers)
            
            # Форматирование заголовков
            sheet.format('1:1', {
                'textFormat': {'bold': True},
                'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
            })
            
            logger.info(f"Headers set up for {language} language")
            
        except Exception as e:
            logger.error(f"Failed to set up headers for {language}: {e}")
    
    def _detect_language(self, text: str) -> str:
        """
        Определение языка текста по ключевым словам
        
        Args:
            text: Текст для анализа
            
        Returns:
            str: Код языка ('ru', 'en', 'pl')
        """
        text_lower = text.lower()
        
        # Польские индикаторы
        polish_indicators = ['ą', 'ć', 'ę', 'ł', 'ń', 'ó', 'ś', 'ź', 'ż', 'praca', 'doświadczenie', 'umiejętności']
        polish_score = sum(1 for indicator in polish_indicators if indicator in text_lower)
        
        # Русские индикаторы
        russian_indicators = ['работа', 'опыт', 'навыки', 'проект', 'технологии', 'разработка', 'программирование']
        russian_score = sum(1 for indicator in russian_indicators if indicator in text_lower)
        
        # Английские индикаторы
        english_indicators = ['work', 'experience', 'skills', 'project', 'technology', 'development', 'programming']
        english_score = sum(1 for indicator in english_indicators if indicator in text_lower)
        
        # Также проверяем наличие кириллицы
        has_cyrillic = bool(re.search(r'[а-яё]', text_lower))
        if has_cyrillic:
            russian_score += 2
            
        # Проверяем польские специальные символы
        has_polish = bool(re.search(r'[ąćęłńóśźż]', text_lower))
        if has_polish:
            polish_score += 3
        
        # Определяем язык по наибольшему счету
        scores = {'pl': polish_score, 'ru': russian_score, 'en': english_score}
        detected_language = max(scores, key=scores.get)
        
        # Если все счета равны 0, по умолчанию английский
        return detected_language if max(scores.values()) > 0 else 'en'
    
    def _setup_headers(self):
        """Настройка заголовков в таблице результатов"""
        if not self.sheet:
            return
        
        headers = [
            "Дата анализа",
            "ID кандидата", 
            "Имя кандидата",
            "Общий балл",
            "Рекомендация",
            
            # Критерии оценки с форматированным выводом
            "1. Коммуникативные навыки",
            "2. Мотивация к обучению", 
            "3. Профессиональные навыки",
            "4. Аналитическое мышление",
            "5. Умение нестандартно мыслить",
            "6. Командная работа",
            "7. Стрессоустойчивость",
            "8. Адаптивность",
            "9. Креативность",
            "10. Общее впечатление",
            
            # Дополнительные данные
            "Невербальный анализ",
            "Качество видео/аудио",
            "Длительность интервью",
            "Детальная обратная связь"
        ]
        
        try:
            self.sheet.append_row(headers)
            logger.info("Headers set up in results sheet")
        except Exception as e:
            logger.error(f"Failed to set up headers: {e}")
    
    def save_analysis_results(self, analysis: InterviewAnalysis, candidate_info: Optional[Dict] = None) -> bool:
        """
        Сохранение результатов анализа в таблицу с поддержкой языков
        
        Args:
            analysis: Результат анализа интервью
            candidate_info: Дополнительная информация о кандидате (email, phone)
            
        Returns:
            bool: True если сохранение успешно
        """
        try:
            # Определение языка по контенту интервью
            language = self._detect_language(analysis.detailed_feedback)
            logger.info(f"Detected language: {language} for candidate: {analysis.candidate_name}")
            
            # Получение соответствующего листа
            if language not in self.sheets:
                logger.error(f"No sheet found for language: {language}")
                return False
                
            sheet = self.sheets[language]
            
            # Извлечение информации о кандидате
            email = candidate_info.get('email', '') if candidate_info else ''
            phone = candidate_info.get('phone', '') if candidate_info else ''
            
            # Подготовка данных для записи
            row_data = [
                analysis.candidate_name,                       # Имя
                email,                                         # Email
                phone,                                         # Телефон
            ]
            
            # Добавление форматированных оценок по критериям
            criteria_order = [
                EvaluationCriteria.COMMUNICATION_SKILLS,
                EvaluationCriteria.MOTIVATION_LEARNING,
                EvaluationCriteria.PROFESSIONAL_SKILLS, 
                EvaluationCriteria.ANALYTICAL_THINKING,
                EvaluationCriteria.UNCONVENTIONAL_THINKING,
                EvaluationCriteria.TEAMWORK_ABILITY,
                EvaluationCriteria.STRESS_RESISTANCE,
                EvaluationCriteria.ADAPTABILITY,
                EvaluationCriteria.CREATIVITY_INNOVATION,
                EvaluationCriteria.OVERALL_IMPRESSION
            ]
            
            for criterion in criteria_order:
                if criterion in analysis.scores:
                    score_data = analysis.scores[criterion]
                    # Формат: "8/10 - Отличные коммуникативные навыки. Примеры: четкая речь, хороший зрительный контакт"
                    formatted_score = self._format_evaluation(score_data)
                    row_data.append(formatted_score)
                else:
                    row_data.append("Не оценено")
            
            # Финальная оценка и рекомендация
            row_data.extend([
                f"{analysis.total_score}/100",  # Финальная оценка
                analysis.recommendation         # Рекомендация
            ])
            
            # Запись в таблицу
            sheet.append_row(row_data)
            
            logger.info(f"Analysis results saved for candidate: {analysis.candidate_name} in {language} sheet")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save analysis results: {e}")
            return False
    
    def _format_evaluation(self, score_data) -> str:
        """
        Форматирование оценки в требуемом формате
        
        Args:
            score_data: Данные об оценке
            
        Returns:
            str: Форматированная строка "X/10 + объяснение с примерами"
        """
        result = f"{score_data.score}/10 - {score_data.explanation}"
        
        if score_data.specific_examples:
            examples_text = "; ".join(score_data.specific_examples[:3])  # Максимум 3 примера
            result += f" Примеры: {examples_text}"
        
        return result
    
    def _format_nonverbal_analysis(self, analysis: InterviewAnalysis) -> str:
        """Форматирование невербального анализа"""
        nonverbal_parts = []
        
        # Эмоции
        if analysis.emotion_analysis:
            top_emotions = sorted(analysis.emotion_analysis.items(), key=lambda x: x[1], reverse=True)[:3]
            emotions_text = ", ".join([f"{emotion}: {value:.1f}%" for emotion, value in top_emotions])
            nonverbal_parts.append(f"Эмоции: {emotions_text}")
        
        # Зрительный контакт
        nonverbal_parts.append(f"Зрительный контакт: {analysis.eye_contact_percentage:.1f}%")
        
        # Поза и жесты
        nonverbal_parts.append(f"Уверенность позы: {analysis.posture_confidence}/10")
        nonverbal_parts.append(f"Частота жестов: {analysis.gesture_frequency}")
        
        return "; ".join(nonverbal_parts)
    
    def get_analysis_history(self, candidate_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Получение истории анализов
        
        Args:
            candidate_id: ID кандидата для фильтрации (опционально)
            
        Returns:
            List[Dict]: Список результатов анализов
        """
        if not self.sheet:
            logger.error("Results sheet not initialized")
            return []
        
        try:
            records = self.sheet.get_all_records()
            
            if candidate_id:
                records = [r for r in records if r.get("ID кандидата") == candidate_id]
            
            return records
            
        except Exception as e:
            logger.error(f"Failed to get analysis history: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Получение статистики по проведенным анализам
        
        Returns:
            Dict: Статистика анализов
        """
        if not self.sheet:
            return {"error": "Results sheet not initialized"}
        
        try:
            records = self.sheet.get_all_records()
            
            if not records:
                return {"total_interviews": 0}
            
            total_interviews = len(records)
            
            # Подсчет рекомендаций
            recommendations = {}
            total_scores = []
            
            for record in records:
                rec = record.get("Рекомендация", "Неизвестно")
                recommendations[rec] = recommendations.get(rec, 0) + 1
                
                try:
                    score = int(record.get("Общий балл", 0))
                    total_scores.append(score)
                except (ValueError, TypeError):
                    pass
            
            # Средний балл
            avg_score = sum(total_scores) / len(total_scores) if total_scores else 0
            
            return {
                "total_interviews": total_interviews,
                "average_score": round(avg_score, 1),
                "recommendations_breakdown": recommendations,
                "score_distribution": {
                    "excellent": len([s for s in total_scores if s >= 85]),
                    "good": len([s for s in total_scores if 70 <= s < 85]),
                    "average": len([s for s in total_scores if 55 <= s < 70]),
                    "poor": len([s for s in total_scores if s < 55])
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {"error": str(e)}
