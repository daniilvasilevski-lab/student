"""
Автоматический процессор интервью из Google Sheets
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import re

import gspread
from google.oauth2.service_account import Credentials
from langdetect import detect

from ..config.settings import settings
from .integrated_analyzer import IntegratedInterviewAnalyzer
from .cv_analyzer import CVAnalyzer
from .questions_analyzer import QuestionsAnalyzer
from .language_detector import LanguageDetector
from ..models.evaluation_criteria import InterviewAnalysis


logger = logging.getLogger(__name__)


class InterviewProcessor:
    """Автоматический процессор интервью из Google Sheets"""
    
    def __init__(self, openai_client):
        self.openai_client = openai_client
        self.analyzer = IntegratedInterviewAnalyzer(openai_client)
        self.cv_analyzer = CVAnalyzer(openai_client)
        self.questions_analyzer = QuestionsAnalyzer(openai_client)
        self.language_detector = LanguageDetector()
        
        # Настройка Google Sheets
        self.gc = None
        self.setup_google_sheets()
        
        # Мультиязычные листы результатов
        self.result_sheets = {
            'ru': 'Results_ru',
            'en': 'Results_en', 
            'pl': 'Results_pl'
        }
        
        # Колонки входной таблицы
        self.input_columns = {
            'ID': 0,  # A
            'Name': 1,  # B
            'Email': 2,  # C
            'Phone': 3,  # D
            'Preferences': 4,  # E
            'CV_gcs': 5,  # F
            'video_gcs': 6,  # G
            'CV_URL': 7,  # H
            'Video_URL': 8,  # I
            'created_at': 9,  # J
            'Questions_URL': 10,  # K
            'Processed': 11  # L
        }
    
    def setup_google_sheets(self):
        """Настройка подключения к Google Sheets"""
        try:
            if settings.google_service_account_key:
                scope = [
                    "https://spreadsheets.google.com/feeds",
                    "https://www.googleapis.com/auth/drive"
                ]
                
                creds = Credentials.from_service_account_file(
                    settings.google_service_account_key, 
                    scopes=scope
                )
                self.gc = gspread.authorize(creds)
                logger.info("Google Sheets connection established")
            else:
                logger.warning("Google service account key not configured")
        except Exception as e:
            logger.error(f"Failed to setup Google Sheets: {e}")
    
    async def scan_for_unprocessed_interviews(self) -> List[Dict[str, Any]]:
        """Сканирует таблицу на наличие необработанных интервью"""
        if not self.gc:
            logger.error("Google Sheets not configured")
            return []
        
        try:
            # Открываем таблицу
            sheet = self.gc.open_by_url(settings.source_sheet_url).sheet1
            
            # Получаем все данные
            all_values = sheet.get_all_values()
            
            if not all_values:
                logger.info("No data found in source sheet")
                return []
            
            headers = all_values[0]
            rows = all_values[1:]  # Пропускаем заголовки
            
            unprocessed = []
            
            for row_idx, row in enumerate(rows, start=2):  # +2 because 1-indexed and skip header
                # Проверяем, что у нас достаточно колонок
                if len(row) <= self.input_columns['Processed']:
                    continue
                
                # Проверяем поле Processed
                processed_value = row[self.input_columns['Processed']].strip()
                
                if not processed_value or processed_value != '1':
                    # Это необработанная запись
                    interview_data = {
                        'row_number': row_idx,
                        'id': row[self.input_columns['ID']],
                        'name': row[self.input_columns['Name']],
                        'email': row[self.input_columns['Email']],
                        'phone': row[self.input_columns['Phone']],
                        'preferences': row[self.input_columns['Preferences']],
                        'cv_url': row[self.input_columns['CV_URL']],
                        'video_url': row[self.input_columns['Video_URL']],
                        'questions_url': row[self.input_columns['Questions_URL']],
                        'created_at': row[self.input_columns['created_at']]
                    }
                    
                    # Проверяем, что есть необходимые URL
                    if interview_data['video_url'] and interview_data['video_url'].strip():
                        unprocessed.append(interview_data)
                        logger.info(f"Found unprocessed interview: {interview_data['name']} (Row {row_idx})")
            
            logger.info(f"Found {len(unprocessed)} unprocessed interviews")
            return unprocessed
            
        except Exception as e:
            logger.error(f"Error scanning for unprocessed interviews: {e}")
            return []
    
    async def detect_interview_language(self, video_url: str, cv_url: str = None, questions_url: str = None) -> str:
        """Определяет язык интервью"""
        try:
            # 1. Пытаемся определить язык по CV
            if cv_url:
                cv_analysis = await self.cv_analyzer.analyze_cv(cv_url, "temp_candidate")
                if cv_analysis.get('detected_language'):
                    language = cv_analysis['detected_language']
                    logger.info(f"Language detected from CV: {language}")
                    return language
            
            # 2. Пытаемся определить язык по вопросам
            if questions_url:
                questions_analysis = await self.questions_analyzer.analyze_questions(questions_url, "temp_candidate")
                if questions_analysis.get('detected_language'):
                    language = questions_analysis['detected_language']
                    logger.info(f"Language detected from questions: {language}")
                    return language
            
            # 3. Используем детектор языка по видео (если доступен)
            language = await self.language_detector.detect_from_video(video_url)
            if language:
                logger.info(f"Language detected from video: {language}")
                return language
            
            # 4. По умолчанию возвращаем русский
            logger.warning("Could not detect language, defaulting to 'ru'")
            return 'ru'
            
        except Exception as e:
            logger.error(f"Error detecting language: {e}")
            return 'ru'  # По умолчанию русский
    
    async def process_single_interview(self, interview_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Обрабатывает одно интервью"""
        try:
            logger.info(f"Processing interview for {interview_data['name']} (ID: {interview_data['id']})")
            
            # 1. Определяем язык интервью
            language = await self.detect_interview_language(
                interview_data['video_url'],
                interview_data.get('cv_url'),
                interview_data.get('questions_url')
            )
            
            # 2. Подготавливаем информацию о кандидате
            candidate_info = {
                'id': interview_data['id'],
                'name': interview_data['name'],
                'email': interview_data['email'],
                'phone': interview_data['phone'],
                'preferences': interview_data['preferences'],
                'language': language
            }
            
            # 3. Анализируем CV (если есть)
            cv_analysis = None
            if interview_data.get('cv_url'):
                cv_analysis = await self.cv_analyzer.analyze_cv(
                    interview_data['cv_url'], 
                    interview_data['name']
                )
                candidate_info['cv_analysis'] = cv_analysis
            
            # 4. Анализируем вопросы (если есть)
            questions_analysis = None
            if interview_data.get('questions_url'):
                questions_analysis = await self.questions_analyzer.analyze_questions(
                    interview_data['questions_url'],
                    interview_data['name']
                )
                candidate_info['questions_analysis'] = questions_analysis
            
            # 5. Запускаем основной анализ интервью
            analysis_result = await self.analyzer.analyze_interview(
                interview_data['video_url'],
                candidate_info
            )
            
            # 6. Добавляем метаданные
            analysis_result.interview_language = language
            analysis_result.source_row = interview_data['row_number']
            analysis_result.processed_at = datetime.now().isoformat()
            
            logger.info(f"Successfully processed interview for {interview_data['name']}")
            return {
                'interview_data': interview_data,
                'analysis_result': analysis_result,
                'language': language
            }
            
        except Exception as e:
            logger.error(f"Error processing interview for {interview_data['name']}: {e}")
            return None
    
    async def save_results_to_sheet(self, result: Dict[str, Any]) -> bool:
        """Сохраняет результаты в соответствующий языковой лист"""
        if not self.gc:
            logger.error("Google Sheets not configured")
            return False
        
        try:
            language = result['language']
            analysis_result = result['analysis_result']
            interview_data = result['interview_data']
            
            # Определяем имя листа для результатов
            sheet_name = self.result_sheets.get(language, 'Results_ru')
            
            # Открываем нужный лист
            spreadsheet = self.gc.open_by_url(settings.results_sheet_url)
            try:
                worksheet = spreadsheet.worksheet(sheet_name)
            except gspread.WorksheetNotFound:
                # Создаем лист если его нет
                worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=26)
                # Добавляем заголовки
                headers = self._get_results_headers(language)
                worksheet.append_row(headers)
            
            # Формируем строку с результатами
            results_row = self._format_results_row(interview_data, analysis_result, language)
            
            # Добавляем строку
            worksheet.append_row(results_row)
            
            logger.info(f"Results saved to {sheet_name} for {interview_data['name']}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving results to sheet: {e}")
            return False
    
    def _get_results_headers(self, language: str) -> List[str]:
        """Возвращает заголовки для листа результатов"""
        if language == 'en':
            return [
                'Candidate_ID', 'Name', 'Email', 'Interview_Date', 'Total_Score', 'Recommendation',
                'Communication_Skills', 'Technical_Knowledge', 'Problem_Solving', 'Motivation',
                'Cultural_Fit', 'Leadership', 'Adaptability', 'Professionalism', 
                'Self_Presentation', 'Overall_Impression', 'Video_Quality', 'Audio_Quality',
                'Eye_Contact_%', 'Gesture_Frequency', 'Emotions', 'Speech_Rate', 'Language_Detected',
                'Detailed_Feedback', 'Processed_At', 'Source_Row'
            ]
        elif language == 'pl':
            return [
                'ID_Kandydata', 'Imię', 'Email', 'Data_Rozmowy', 'Wynik_Całkowity', 'Rekomendacja',
                'Umiejętności_Komunikacyjne', 'Wiedza_Techniczna', 'Rozwiązywanie_Problemów', 'Motywacja',
                'Dopasowanie_Kulturowe', 'Przywództwo', 'Adaptacyjność', 'Profesjonalizm',
                'Autoprezentacja', 'Ogólne_Wrażenie', 'Jakość_Wideo', 'Jakość_Audio',
                'Kontakt_Wzrokowy_%', 'Częstość_Gestów', 'Emocje', 'Tempo_Mowy', 'Wykryty_Język',
                'Szczegółowa_Opinia', 'Przetworzono_O', 'Wiersz_Źródłowy'
            ]
        else:  # ru
            return [
                'ID_Кандидата', 'Имя', 'Email', 'Дата_Интервью', 'Общий_Балл', 'Рекомендация',
                'Коммуникативные_Навыки', 'Технические_Знания', 'Решение_Проблем', 'Мотивация',
                'Культурное_Соответствие', 'Лидерство', 'Адаптивность', 'Профессионализм',
                'Самопрезентация', 'Общее_Впечатление', 'Качество_Видео', 'Качество_Аудио',
                'Контакт_Глазами_%', 'Частота_Жестов', 'Эмоции', 'Темп_Речи', 'Определенный_Язык',
                'Подробная_Обратная_Связь', 'Обработано_В', 'Исходная_Строка'
            ]
    
    def _format_results_row(self, interview_data: Dict[str, Any], analysis: InterviewAnalysis, language: str) -> List[str]:
        """Форматирует строку результатов для записи в таблицу"""
        # Извлекаем баллы по критериям
        scores = analysis.scores if hasattr(analysis, 'scores') else {}
        
        # Базовая информация
        row = [
            interview_data['id'],
            interview_data['name'],
            interview_data['email'],
            interview_data.get('created_at', ''),
            str(getattr(analysis, 'total_score', 0)),
            getattr(analysis, 'recommendation', '')
        ]
        
        # Баллы по критериям (10 критериев)
        criteria_order = [
            'communication_skills', 'technical_knowledge', 'problem_solving', 'motivation',
            'cultural_fit', 'leadership', 'adaptability', 'professionalism', 
            'self_presentation', 'overall_impression'
        ]
        
        for criterion in criteria_order:
            score = scores.get(criterion, {}).get('score', 0) if scores else 0
            row.append(str(score))
        
        # Дополнительные метрики
        row.extend([
            str(getattr(analysis, 'video_quality', 0)),
            str(getattr(analysis, 'audio_quality', 0)),
            str(getattr(analysis, 'eye_contact_percentage', 0)),
            str(getattr(analysis, 'gesture_frequency', 0)),
            str(getattr(analysis, 'emotion_analysis', {})),
            str(getattr(analysis, 'speech_pace', '')),
            language,
            getattr(analysis, 'detailed_feedback', ''),
            getattr(analysis, 'processed_at', ''),
            str(interview_data['row_number'])
        ])
        
        return row
    
    async def mark_as_processed(self, interview_data: Dict[str, Any]) -> bool:
        """Отмечает интервью как обработанное"""
        if not self.gc:
            logger.error("Google Sheets not configured")
            return False
        
        try:
            # Открываем исходную таблицу
            sheet = self.gc.open_by_url(settings.source_sheet_url).sheet1
            
            # Обновляем ячейку Processed
            processed_column = chr(ord('A') + self.input_columns['Processed'])
            cell_address = f"{processed_column}{interview_data['row_number']}"
            
            sheet.update(cell_address, "1")
            
            logger.info(f"Marked interview as processed: {interview_data['name']} (Row {interview_data['row_number']})")
            return True
            
        except Exception as e:
            logger.error(f"Error marking interview as processed: {e}")
            return False
    
    async def process_all_unprocessed(self) -> Dict[str, int]:
        """Обрабатывает все необработанные интервью"""
        logger.info("Starting batch processing of unprocessed interviews")
        
        stats = {
            'found': 0,
            'processed': 0,
            'failed': 0,
            'saved': 0
        }
        
        try:
            # 1. Сканируем необработанные интервью
            unprocessed_interviews = await self.scan_for_unprocessed_interviews()
            stats['found'] = len(unprocessed_interviews)
            
            if not unprocessed_interviews:
                logger.info("No unprocessed interviews found")
                return stats
            
            # 2. Обрабатываем каждое интервью
            for interview_data in unprocessed_interviews:
                try:
                    # Обрабатываем интервью
                    result = await self.process_single_interview(interview_data)
                    
                    if result:
                        stats['processed'] += 1
                        
                        # Сохраняем результаты
                        if await self.save_results_to_sheet(result):
                            stats['saved'] += 1
                            
                            # Отмечаем как обработанное
                            await self.mark_as_processed(interview_data)
                        else:
                            logger.error(f"Failed to save results for {interview_data['name']}")
                    else:
                        stats['failed'] += 1
                        logger.error(f"Failed to process interview for {interview_data['name']}")
                
                except Exception as e:
                    stats['failed'] += 1
                    logger.error(f"Error processing interview {interview_data['name']}: {e}")
                
                # Небольшая пауза между обработками
                await asyncio.sleep(2)
            
            logger.info(f"Batch processing completed. Stats: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error in batch processing: {e}")
            return stats


async def create_interview_processor(openai_client) -> InterviewProcessor:
    """Фабрика для создания процессора интервью"""
    return InterviewProcessor(openai_client)
