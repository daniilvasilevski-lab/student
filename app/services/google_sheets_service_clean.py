"""
Сервис для работы с Google Sheets
Чистая версия без синтаксических ошибок
"""

import os
import logging
from typing import List, Dict, Any, Optional
import gspread
from google.oauth2.service_account import Credentials

from ..models.evaluation_criteria import InterviewAnalysis

logger = logging.getLogger(__name__)


class GoogleSheetsService:
    """Сервис для работы с Google Sheets API"""
    
    def __init__(self):
        self.credentials = None
        self.client = None
        self.spreadsheet = None
        self.worksheet = None
        
    async def _ensure_authenticated(self):
        """Обеспечение аутентификации и подключения к Google Sheets"""
        if self.client is None:
            try:
                # Получение учетных данных из переменных окружения
                creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
                if creds_json:
                    # Загрузка из JSON строки
                    import json
                    creds_dict = json.loads(creds_json)
                    self.credentials = Credentials.from_service_account_info(
                        creds_dict,
                        scopes=['https://spreadsheets.google.com/feeds',
                               'https://www.googleapis.com/auth/drive']
                    )
                else:
                    # Загрузка из файла
                    creds_file = os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')
                    self.credentials = Credentials.from_service_account_file(
                        creds_file,
                        scopes=['https://spreadsheets.google.com/feeds',
                               'https://www.googleapis.com/auth/drive']
                    )
                
                self.client = gspread.authorize(self.credentials)
                logger.info("Google Sheets authentication successful")
                
            except Exception as e:
                logger.error(f"Google Sheets authentication failed: {e}")
                raise
        
        if self.spreadsheet is None:
            spreadsheet_id = os.getenv('SPREADSHEET_ID')
            if not spreadsheet_id:
                raise ValueError("SPREADSHEET_ID environment variable is required")
                
            self.spreadsheet = self.client.open_by_key(spreadsheet_id)
            
            sheet_name = os.getenv('SHEET_NAME', 'Кандидаты')
            self.worksheet = self.spreadsheet.worksheet(sheet_name)
            
            logger.info(f"Connected to spreadsheet: {spreadsheet_id}, sheet: {sheet_name}")
    
    async def get_unprocessed_interviews(self) -> List[Dict[str, Any]]:
        """Получение списка необработанных интервью"""
        await self._ensure_authenticated()
        
        try:
            all_records = self.worksheet.get_all_records()
            
            unprocessed = []
            for idx, record in enumerate(all_records, start=2):  # Начинаем с 2, т.к. 1 строка - заголовки
                # Проверяем наличие URL видео и отсутствие флага обработки
                if (record.get('video_url') and 
                    record.get('processed') != '1'):
                    record['row_index'] = idx
                    unprocessed.append(record)
            
            logger.info(f"Found {len(unprocessed)} unprocessed interviews")
            return unprocessed
            
        except Exception as e:
            logger.error(f"Failed to fetch unprocessed interviews: {e}")
            raise
    
    async def setup_analysis_columns(self):
        """Настройка колонок для результатов анализа"""
        await self._ensure_authenticated()
        
        try:
            headers = self.worksheet.row_values(1)
            
            # Определение необходимых колонок для анализа
            analysis_columns = [
                'total_score',
                'weighted_score', 
                'recommendation',
                'detailed_feedback',
                'communication_skills_score',
                'communication_skills_explanation',
                'motivation_learning_score',
                'motivation_learning_explanation',
                'professional_skills_score',
                'professional_skills_explanation',
                'analytical_thinking_score',
                'analytical_thinking_explanation',
                'unconventional_thinking_score',
                'unconventional_thinking_explanation',
                'teamwork_ability_score',
                'teamwork_ability_explanation',
                'stress_resistance_score',
                'stress_resistance_explanation',
                'adaptability_score',
                'adaptability_explanation',
                'creativity_innovation_score',
                'creativity_innovation_explanation',
                'overall_impression_score',
                'overall_impression_explanation',
                'eye_contact_percentage',
                'gesture_frequency',
                'posture_confidence',
                'speech_pace',
                'emotion_analysis',
                'analysis_timestamp',
                'ai_model_version',
                'processed'
            ]
            
            # Добавление недостающих колонок
            new_headers = headers.copy()
            for column in analysis_columns:
                if column not in headers:
                    new_headers.append(column)
            
            # Обновление заголовков если нужно
            if len(new_headers) > len(headers):
                # Расширение листа если нужно
                current_cols = len(headers)
                needed_cols = len(new_headers)
                if needed_cols > current_cols:
                    self.worksheet.add_cols(needed_cols - current_cols)
                
                # Обновление заголовков
                self.worksheet.update('1:1', [new_headers])
                logger.info(f"Added {len(new_headers) - len(headers)} new analysis columns")
            else:
                logger.info("Analysis columns already exist")
                
        except Exception as e:
            logger.error(f"Failed to setup analysis columns: {e}")
            raise
    
    async def save_analysis_results(self, row_index: int, analysis: InterviewAnalysis):
        """Сохранение результатов анализа в Google Sheets"""
        await self._ensure_authenticated()
        
        try:
            # Получение заголовков для определения позиций колонок
            headers = self.worksheet.row_values(1)
            
            # Подготовка данных для записи
            update_data = {}
            
            # Оценки по критериям
            for criterion, score_obj in analysis.scores.items():
                score_col = f"{criterion.value}_score"
                explanation_col = f"{criterion.value}_explanation"
                
                if score_col in headers:
                    update_data[score_col] = score_obj.score
                if explanation_col in headers:
                    update_data[explanation_col] = score_obj.explanation
            
            # Общие метрики
            general_metrics = {
                'total_score': analysis.total_score,
                'weighted_score': round(analysis.weighted_score, 2),
                'recommendation': analysis.recommendation,
                'detailed_feedback': analysis.detailed_feedback,
                'eye_contact_percentage': round(analysis.eye_contact_percentage, 1),
                'gesture_frequency': analysis.gesture_frequency,
                'posture_confidence': analysis.posture_confidence,
                'speech_pace': analysis.speech_pace,
                'emotion_analysis': str(analysis.emotion_analysis),
                'analysis_timestamp': analysis.analysis_timestamp,
                'ai_model_version': analysis.ai_model_version,
                'processed': '1'  # Помечаем как обработанное
            }
            
            for key, value in general_metrics.items():
                if key in headers:
                    update_data[key] = value
            
            # Обновление строки
            if update_data:
                # Создание списка значений для обновления
                row_values = [''] * len(headers)
                for column, value in update_data.items():
                    if column in headers:
                        col_index = headers.index(column)
                        row_values[col_index] = str(value)
                
                # Обновление только заполненных ячеек
                updates = []
                for i, value in enumerate(row_values):
                    if value:  # Обновляем только непустые значения
                        col_letter = self._number_to_column_letter(i + 1)
                        cell_range = f"{col_letter}{row_index}"
                        updates.append({
                            'range': cell_range,
                            'values': [[value]]
                        })
                
                # Пакетное обновление
                if updates:
                    self.worksheet.batch_update(updates)
                
                logger.info(f"Analysis results saved for row {row_index}")
            else:
                logger.warning(f"No matching columns found for analysis data in row {row_index}")
                
        except Exception as e:
            logger.error(f"Failed to save analysis results for row {row_index}: {e}")
            raise
    
    def _number_to_column_letter(self, n: int) -> str:
        """Конвертация номера колонки в букву (1 -> A, 2 -> B, etc.)"""
        result = ""
        while n > 0:
            n -= 1
            result = chr(65 + n % 26) + result
            n //= 26
        return result
    
    async def get_interview_by_id(self, interview_id: str) -> Optional[Dict[str, Any]]:
        """Получение интервью по ID"""
        await self._ensure_authenticated()
        
        try:
            all_records = self.worksheet.get_all_records()
            
            for idx, record in enumerate(all_records, start=2):
                if str(record.get('id', '')) == str(interview_id):
                    record['row_index'] = idx
                    return record
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to fetch interview by ID {interview_id}: {e}")
            raise
    
    async def mark_as_processed(self, row_index: int):
        """Пометить интервью как обработанное"""
        await self._ensure_authenticated()
        
        try:
            headers = self.worksheet.row_values(1)
            
            if 'processed' in headers:
                col_index = headers.index('processed') + 1
                col_letter = self._number_to_column_letter(col_index)
                cell_range = f"{col_letter}{row_index}"
                
                self.worksheet.update(cell_range, '1')
                logger.info(f"Marked row {row_index} as processed")
            else:
                logger.warning("'processed' column not found")
                
        except Exception as e:
            logger.error(f"Failed to mark row {row_index} as processed: {e}")
            raise
    
    async def get_analysis_statistics(self) -> Dict[str, Any]:
        """Получение статистики анализа"""
        await self._ensure_authenticated()
        
        try:
            all_records = self.worksheet.get_all_records()
            
            total_interviews = len(all_records)
            processed_interviews = sum(1 for record in all_records if record.get('processed') == '1')
            unprocessed_interviews = total_interviews - processed_interviews
            
            # Статистика по оценкам (для обработанных интервью)
            total_scores = []
            recommendations = {}
            
            for record in all_records:
                if record.get('processed') == '1':
                    total_score = record.get('total_score')
                    if total_score and str(total_score).isdigit():
                        total_scores.append(int(total_score))
                    
                    recommendation = record.get('recommendation', 'Unknown')
                    recommendations[recommendation] = recommendations.get(recommendation, 0) + 1
            
            average_score = sum(total_scores) / len(total_scores) if total_scores else 0
            
            return {
                'total_interviews': total_interviews,
                'processed_interviews': processed_interviews,
                'unprocessed_interviews': unprocessed_interviews,
                'average_score': round(average_score, 2),
                'score_distribution': {
                    'excellent': len([s for s in total_scores if s >= 80]),
                    'good': len([s for s in total_scores if 70 <= s < 80]),
                    'average': len([s for s in total_scores if 60 <= s < 70]),
                    'below_average': len([s for s in total_scores if s < 60])
                },
                'recommendations': recommendations
            }
            
        except Exception as e:
            logger.error(f"Failed to get analysis statistics: {e}")
            raise