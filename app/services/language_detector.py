"""
Детектор языка для интервью
"""

import asyncio
import logging
from typing import Optional, Dict, Any
import re
import tempfile
import os

from langdetect import detect, detect_langs
import whisper
import yt_dlp
import requests

from ..config.settings import settings


logger = logging.getLogger(__name__)


class LanguageDetector:
    """Детектор языка интервью"""
    
    def __init__(self):
        self.whisper_model = None
        self.supported_languages = {
            'ru': ['ru', 'russian'],
            'en': ['en', 'english'],
            'pl': ['pl', 'polish']
        }
        
        # Языковые паттерны для дополнительной проверки
        self.language_patterns = {
            'ru': [
                r'\b(привет|здравствуй|добро пожаловать|спасибо|пожалуйста|извините|меня зовут|работа|компания|опыт|навыки)\b',
                r'\b(что|как|где|когда|почему|который|какой|кто|куда|откуда)\b',
                r'\b(я|ты|он|она|мы|вы|они|мой|твой|его|её|наш|ваш|их)\b'
            ],
            'en': [
                r'\b(hello|hi|welcome|thank|please|sorry|excuse|my name|work|company|experience|skills)\b',
                r'\b(what|how|where|when|why|which|who|whom|whose)\b',
                r'\b(i|you|he|she|we|they|my|your|his|her|our|their)\b'
            ],
            'pl': [
                r'\b(cześć|dzień dobry|witamy|dziękuję|proszę|przepraszam|nazywam się|praca|firma|doświadczenie|umiejętności)\b',
                r'\b(co|jak|gdzie|kiedy|dlaczego|który|jaki|kto|dokąd|skąd)\b',
                r'\b(ja|ty|on|ona|my|wy|oni|mój|twój|jego|jej|nasz|wasz|ich)\b'
            ]
        }
    
    def _load_whisper_model(self):
        """Загружает модель Whisper для транскрипции"""
        if not self.whisper_model:
            try:
                model_name = settings.whisper_model
                logger.info(f"Loading Whisper model: {model_name}")
                self.whisper_model = whisper.load_model(model_name)
                logger.info("Whisper model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load Whisper model: {e}")
    
    async def detect_from_text(self, text: str) -> Optional[str]:
        """Определяет язык по тексту"""
        if not text or len(text.strip()) < 10:
            return None
        
        try:
            # 1. Используем langdetect
            detected = detect(text.lower())
            logger.info(f"Langdetect result: {detected}")
            
            # Маппим результат на поддерживаемые языки
            if detected in ['ru', 'russian']:
                return 'ru'
            elif detected in ['en', 'english']:
                return 'en'
            elif detected in ['pl', 'polish']:
                return 'pl'
            
            # 2. Дополнительная проверка по паттернам
            pattern_scores = {}
            for lang, patterns in self.language_patterns.items():
                score = 0
                for pattern in patterns:
                    matches = len(re.findall(pattern, text.lower(), re.IGNORECASE))
                    score += matches
                pattern_scores[lang] = score
            
            # Выбираем язык с наибольшим количеством совпадений
            if pattern_scores:
                best_lang = max(pattern_scores, key=pattern_scores.get)
                if pattern_scores[best_lang] > 0:
                    logger.info(f"Pattern matching result: {best_lang} (score: {pattern_scores[best_lang]})")
                    return best_lang
            
            # 3. По умолчанию русский
            logger.warning(f"Could not reliably detect language from text, defaulting to 'ru'")
            return 'ru'
            
        except Exception as e:
            logger.error(f"Error detecting language from text: {e}")
            return 'ru'
    
    async def _download_audio_sample(self, video_url: str, duration: int = 60) -> Optional[str]:
        """Скачивает аудио образец из видео"""
        try:
            # Создаем временный файл
            temp_dir = settings.temp_dir
            os.makedirs(temp_dir, exist_ok=True)
            
            temp_audio = os.path.join(temp_dir, f"audio_sample_{hash(video_url)}.mp3")
            
            # Настройки yt-dlp для скачивания только аудио
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': temp_audio,
                'extractaudio': True,
                'audioformat': 'mp3',
                'quiet': True,
                'no_warnings': True,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                # Ограничиваем длительность для экономии времени
                'external_downloader_args': {
                    'ffmpeg': ['-t', str(duration)]
                }
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
            
            # Проверяем, что файл создался
            if os.path.exists(temp_audio):
                logger.info(f"Audio sample downloaded: {temp_audio}")
                return temp_audio
            else:
                # Иногда yt-dlp создает файл с другим расширением
                base_name = os.path.splitext(temp_audio)[0]
                for ext in ['.m4a', '.webm', '.ogg', '.wav']:
                    alt_file = base_name + ext
                    if os.path.exists(alt_file):
                        logger.info(f"Audio sample found with different extension: {alt_file}")
                        return alt_file
                
                logger.error("Audio file not found after download")
                return None
            
        except Exception as e:
            logger.error(f"Error downloading audio sample: {e}")
            return None
    
    async def _transcribe_audio_sample(self, audio_file: str) -> Optional[str]:
        """Транскрибирует аудио образец"""
        try:
            self._load_whisper_model()
            
            if not self.whisper_model:
                logger.error("Whisper model not available")
                return None
            
            # Транскрибируем с автоопределением языка
            result = self.whisper_model.transcribe(
                audio_file,
                language=None,  # Автоопределение
                task='transcribe',
                fp16=False
            )
            
            transcript = result.get('text', '').strip()
            detected_language = result.get('language')
            
            logger.info(f"Whisper transcription: {transcript[:100]}...")
            logger.info(f"Whisper detected language: {detected_language}")
            
            return transcript
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return None
        finally:
            # Удаляем временный файл
            try:
                if audio_file and os.path.exists(audio_file):
                    os.remove(audio_file)
                    logger.info(f"Cleaned up temporary audio file: {audio_file}")
            except Exception as e:
                logger.warning(f"Could not clean up audio file {audio_file}: {e}")
    
    async def detect_from_video(self, video_url: str) -> Optional[str]:
        """Определяет язык из видео"""
        try:
            logger.info(f"Detecting language from video: {video_url}")
            
            # 1. Скачиваем образец аудио
            audio_file = await self._download_audio_sample(video_url, duration=120)  # 2 минуты
            
            if not audio_file:
                logger.warning("Could not download audio sample for language detection")
                return None
            
            # 2. Транскрибируем аудио
            transcript = await self._transcribe_audio_sample(audio_file)
            
            if not transcript:
                logger.warning("Could not transcribe audio for language detection")
                return None
            
            # 3. Определяем язык по транскрипту
            language = await self.detect_from_text(transcript)
            
            logger.info(f"Language detected from video: {language}")
            return language
            
        except Exception as e:
            logger.error(f"Error detecting language from video: {e}")
            return None
    
    async def detect_from_cv(self, cv_text: str) -> Optional[str]:
        """Определяет язык из текста CV"""
        return await self.detect_from_text(cv_text)
    
    async def detect_from_questions(self, questions_text: str) -> Optional[str]:
        """Определяет язык из текста вопросов"""
        return await self.detect_from_text(questions_text)
    
    def get_language_confidence(self, text: str) -> Dict[str, float]:
        """Возвращает уверенность в определении языка для каждого поддерживаемого языка"""
        if not text or len(text.strip()) < 10:
            return {'ru': 0.33, 'en': 0.33, 'pl': 0.33}
        
        try:
            # Используем langdetect для получения вероятностей
            lang_probs = detect_langs(text.lower())
            
            confidence = {'ru': 0.0, 'en': 0.0, 'pl': 0.0}
            
            for lang_prob in lang_probs:
                lang = lang_prob.lang
                prob = lang_prob.prob
                
                if lang in ['ru', 'russian']:
                    confidence['ru'] = prob
                elif lang in ['en', 'english']:
                    confidence['en'] = prob
                elif lang in ['pl', 'polish']:
                    confidence['pl'] = prob
            
            # Нормализуем вероятности
            total = sum(confidence.values())
            if total > 0:
                confidence = {k: v/total for k, v in confidence.items()}
            else:
                confidence = {'ru': 0.33, 'en': 0.33, 'pl': 0.33}
            
            return confidence
            
        except Exception as e:
            logger.error(f"Error calculating language confidence: {e}")
            return {'ru': 0.33, 'en': 0.33, 'pl': 0.33}
    
    async def detect_with_confidence(self, text: str) -> Dict[str, Any]:
        """Возвращает результат определения языка с уверенностью"""
        detected_lang = await self.detect_from_text(text)
        confidence = self.get_language_confidence(text)
        
        return {
            'detected_language': detected_lang,
            'confidence': confidence,
            'best_confidence': max(confidence.values()) if confidence else 0.0
        }


async def create_language_detector() -> LanguageDetector:
    """Фабрика для создания детектора языка"""
    return LanguageDetector()
