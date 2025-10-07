"""
Сервис для обработки аудио из интервью
Извлекает аудио из видео, анализирует речь и создает транскрипт
"""

import os
import tempfile
import logging
import asyncio
import subprocess
from typing import Dict, List, Any, Optional, Tuple
import speech_recognition as sr
import librosa
import numpy as np
from pydub import AudioSegment
import whisper
import aiofiles
import aiohttp
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class AudioProcessor:
    """Процессор для анализа аудио из интервью"""
    
    def __init__(self):
        # Инициализация распознавателя речи
        self.recognizer = sr.Recognizer()
        
        # Настройки для русского языка
        self.language_settings = {
            'ru': {
                'speech_rate_normal': (140, 180),  # слов в минуту
                'pause_thresholds': (0.3, 1.5),   # секунды
                'pitch_range_normal': (80, 300),   # Hz
            },
            'en': {
                'speech_rate_normal': (150, 200),
                'pause_thresholds': (0.2, 1.0),
                'pitch_range_normal': (85, 255),
            }
        }
        
        # Загрузка модели Whisper для более точного распознавания
        try:
            self.whisper_model = whisper.load_model("base")
            logger.info("Whisper model loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to load Whisper model: {e}")
            self.whisper_model = None
    
    async def process_audio(self, video_url: str, language: str = 'ru') -> Dict[str, Any]:
        """
        Основной метод обработки аудио
        
        Args:
            video_url: URL видео для извлечения аудио
            language: Язык распознавания ('ru', 'en')
            
        Returns:
            Dict с результатами анализа аудио
        """
        logger.info(f"Starting audio processing for URL: {video_url}")
        
        try:
            # 1. Извлечение аудио из видео
            audio_path = await self._extract_audio_from_video(video_url)
            
            # 2. Предобработка аудио
            processed_audio_path = await self._preprocess_audio(audio_path)
            
            # 3. Создание транскрипта
            transcript_data = await self._create_transcript(processed_audio_path, language)
            
            # 4. Анализ аудио характеристик
            audio_features = await self._analyze_audio_features(processed_audio_path, language)
            
            # 5. Лингвистический анализ транскрипта
            linguistic_analysis = await self._analyze_linguistic_features(
                transcript_data, language
            )
            
            # 6. Объединение результатов
            results = {
                **transcript_data,
                **audio_features,
                **linguistic_analysis,
                "audio_quality": await self._assess_audio_quality(processed_audio_path)
            }
            
            # 7. Очистка временных файлов
            await self._cleanup_temp_files(audio_path, processed_audio_path)
            
            logger.info("Audio processing completed successfully")
            return results
            
        except Exception as e:
            logger.error(f"Audio processing failed: {str(e)}")
            raise e
    
    async def _extract_audio_from_video(self, video_url: str) -> str:
        """Извлечение аудио из видео"""
        try:
            # Создаем временные файлы
            video_temp = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
            audio_temp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            
            video_path = video_temp.name
            audio_path = audio_temp.name
            
            video_temp.close()
            audio_temp.close()
            
            # Скачиваем видео
            timeout = aiohttp.ClientTimeout(total=300)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(video_url) as response:
                    if response.status != 200:
                        raise ValueError(f"Failed to download video: HTTP {response.status}")
                    
                    async with aiofiles.open(video_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            await f.write(chunk)
            
            # Извлекаем аудио с помощью ffmpeg
            cmd = [
                'ffmpeg', '-i', video_path,
                '-vn',  # Без видео
                '-acodec', 'pcm_s16le',  # WAV формат
                '-ar', '16000',  # 16 kHz sample rate
                '-ac', '1',  # Моно
                '-y',  # Перезаписать выходной файл
                audio_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise RuntimeError(f"FFmpeg failed: {stderr.decode()}")
            
            # Очищаем видео файл
            os.unlink(video_path)
            
            logger.info(f"Audio extracted to: {audio_path}")
            return audio_path
            
        except Exception as e:
            logger.error(f"Failed to extract audio: {e}")
            raise e
    
    async def _preprocess_audio(self, audio_path: str) -> str:
        """Предобработка аудио для улучшения качества распознавания"""
        try:
            # Загружаем аудио
            audio_segment = AudioSegment.from_wav(audio_path)
            
            # Нормализация громкости
            normalized_audio = audio_segment.normalize()
            
            # Удаление тишины в начале и конце
            trimmed_audio = normalized_audio.strip_silence(
                silence_len=1000,  # 1 секунда тишины
                silence_thresh=-40  # dB
            )
            
            # Фильтрация шума (базовая)
            # Применяем high-pass фильтр для удаления низкочастотного шума
            filtered_audio = trimmed_audio.high_pass_filter(80)
            
            # Сохраняем обработанное аудио
            processed_path = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
            filtered_audio.export(processed_path, format="wav")
            
            logger.info(f"Audio preprocessed and saved to: {processed_path}")
            return processed_path
            
        except Exception as e:
            logger.error(f"Audio preprocessing failed: {e}")
            # Возвращаем оригинальный файл если предобработка не удалась
            return audio_path
    
    async def _create_transcript(self, audio_path: str, language: str) -> Dict[str, Any]:
        """Создание транскрипта речи"""
        try:
            transcript_text = ""
            confidence_scores = []
            
            # Пробуем использовать Whisper (более точный)
            if self.whisper_model:
                try:
                    result = self.whisper_model.transcribe(
                        audio_path,
                        language=language if language in ['ru', 'en'] else None
                    )
                    
                    transcript_text = result['text'].strip()
                    
                    # Извлекаем confidence scores если доступны
                    if 'segments' in result:
                        confidence_scores = [
                            segment.get('avg_logprob', 0.0) 
                            for segment in result['segments']
                        ]
                    
                    logger.info("Transcript created using Whisper")
                    
                except Exception as e:
                    logger.warning(f"Whisper transcription failed: {e}")
                    # Fallback to speech_recognition
                    transcript_text = await self._fallback_speech_recognition(audio_path, language)
            else:
                # Используем speech_recognition как fallback
                transcript_text = await self._fallback_speech_recognition(audio_path, language)
            
            # Анализ качества транскрипта
            transcript_quality = self._assess_transcript_quality(
                transcript_text, confidence_scores
            )
            
            return {
                "transcript": transcript_text,
                "transcript_quality": transcript_quality,
                "word_count": len(transcript_text.split()) if transcript_text else 0,
                "confidence_scores": confidence_scores
            }
            
        except Exception as e:
            logger.error(f"Transcript creation failed: {e}")
            return {
                "transcript": "",
                "transcript_quality": 1,
                "word_count": 0,
                "confidence_scores": []
            }
    
    async def _fallback_speech_recognition(self, audio_path: str, language: str) -> str:
        """Fallback метод распознавания речи"""
        try:
            with sr.AudioFile(audio_path) as source:
                # Подавление шума
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                audio_data = self.recognizer.record(source)
            
            # Карта языков для Google Speech Recognition
            lang_map = {'ru': 'ru-RU', 'en': 'en-US'}
            google_lang = lang_map.get(language, 'ru-RU')
            
            # Распознавание с Google Speech Recognition
            text = self.recognizer.recognize_google(
                audio_data, 
                language=google_lang
            )
            
            logger.info("Transcript created using Google Speech Recognition")
            return text
            
        except sr.UnknownValueError:
            logger.warning("Speech recognition could not understand audio")
            return ""
        except sr.RequestError as e:
            logger.error(f"Speech recognition service error: {e}")
            return ""
    
    def _assess_transcript_quality(self, transcript: str, confidence_scores: List[float]) -> int:
        """Оценка качества транскрипта (1-10)"""
        if not transcript:
            return 1
        
        quality_score = 5  # Базовая оценка
        
        # Оценка по длине транскрипта
        word_count = len(transcript.split())
        if word_count > 50:
            quality_score += 1
        elif word_count < 10:
            quality_score -= 2
        
        # Оценка по confidence scores (если доступны)
        if confidence_scores:
            avg_confidence = sum(confidence_scores) / len(confidence_scores)
            if avg_confidence > -0.5:  # Whisper log probabilities
                quality_score += 2
            elif avg_confidence < -1.5:
                quality_score -= 1
        
        # Простая проверка на связность речи
        sentence_count = transcript.count('.') + transcript.count('!') + transcript.count('?')
        if sentence_count > 0 and word_count / sentence_count > 5:  # Средняя длина предложения
            quality_score += 1
        
        return max(1, min(10, quality_score))
    
    async def _analyze_audio_features(self, audio_path: str, language: str) -> Dict[str, Any]:
        """Анализ аудио характеристик"""
        try:
            # Загружаем аудио с librosa
            y, sr = librosa.load(audio_path, sr=16000)
            
            # Базовые характеристики
            duration = len(y) / sr
            
            # Анализ речевых характеристик
            features = await self._extract_speech_features(y, sr, language)
            
            # Анализ пауз
            pause_analysis = self._analyze_speech_pauses(y, sr, language)
            
            # Анализ энергии и громкости
            energy_analysis = self._analyze_audio_energy(y)
            
            return {
                "duration": duration,
                **features,
                **pause_analysis,
                **energy_analysis
            }
            
        except Exception as e:
            logger.error(f"Audio features analysis failed: {e}")
            return {
                "duration": 0,
                "speech_rate": 0,
                "speech_clarity": 5,
                "average_pitch": 0,
                "pitch_variation": 0,
                "pause_frequency": 0,
                "average_energy": 0
            }
    
    async def _extract_speech_features(self, y: np.ndarray, sr: int, language: str) -> Dict[str, Any]:
        """Извлечение речевых характеристик"""
        try:
            # Анализ основного тона (pitch)
            pitches, magnitudes = librosa.piptrack(y=y, sr=sr, threshold=0.1)
            
            # Извлекаем значимые частоты
            pitch_values = []
            for t in range(pitches.shape[1]):
                index = magnitudes[:, t].argmax()
                pitch = pitches[index, t]
                if pitch > 0:
                    pitch_values.append(pitch)
            
            if pitch_values:
                average_pitch = np.mean(pitch_values)
                pitch_variation = np.std(pitch_values)
            else:
                average_pitch = 0
                pitch_variation = 0
            
            # Анализ темпа речи (приблизительно)
            # Используем спектральный centroid как показатель артикуляции
            spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
            speech_clarity = min(10, max(1, int(np.mean(spectral_centroids) / 1000)))
            
            # Оценка темпа речи (слов в минуту) - приблизительная
            # Базируется на энергии и спектральных характеристиках
            zero_crossings = librosa.feature.zero_crossing_rate(y)[0]
            avg_zcr = np.mean(zero_crossings)
            
            # Эвристическая формула для темпа речи
            estimated_speech_rate = int(avg_zcr * 1000 + 100)  # Примерная оценка
            
            # Нормализуем относительно языковых норм
            lang_settings = self.language_settings.get(language, self.language_settings['ru'])
            normal_range = lang_settings['speech_rate_normal']
            
            if estimated_speech_rate < normal_range[0]:
                speech_rate_assessment = "медленный"
            elif estimated_speech_rate > normal_range[1]:
                speech_rate_assessment = "быстрый"
            else:
                speech_rate_assessment = "нормальный"
            
            return {
                "speech_rate": estimated_speech_rate,
                "speech_rate_assessment": speech_rate_assessment,
                "speech_clarity": speech_clarity,
                "average_pitch": float(average_pitch),
                "pitch_variation": float(pitch_variation)
            }
            
        except Exception as e:
            logger.error(f"Speech features extraction failed: {e}")
            return {
                "speech_rate": 150,
                "speech_rate_assessment": "нормальный",
                "speech_clarity": 5,
                "average_pitch": 150.0,
                "pitch_variation": 30.0
            }
    
    def _analyze_speech_pauses(self, y: np.ndarray, sr: int, language: str) -> Dict[str, Any]:
        """Анализ пауз в речи"""
        try:
            # Определяем пороги тишины
            rms = librosa.feature.rms(y=y)[0]
            silence_threshold = np.percentile(rms, 20)  # 20-й перцентиль как порог тишины
            
            # Находим сегменты тишины
            silent_frames = rms < silence_threshold
            
            # Группируем последовательные тихие фрамы
            pauses = []
            in_pause = False
            pause_start = 0
            
            frame_duration = len(y) / len(silent_frames) / sr  # Длительность одного фрейма
            
            for i, is_silent in enumerate(silent_frames):
                if is_silent and not in_pause:
                    # Начало паузы
                    in_pause = True
                    pause_start = i
                elif not is_silent and in_pause:
                    # Конец паузы
                    pause_duration = (i - pause_start) * frame_duration
                    if pause_duration > 0.1:  # Игнорируем очень короткие паузы
                        pauses.append(pause_duration)
                    in_pause = False
            
            # Анализ пауз
            if pauses:
                avg_pause_duration = np.mean(pauses)
                pause_frequency = len(pauses) / (len(y) / sr / 60)  # Пауз в минуту
                
                # Оценка качества пауз
                lang_settings = self.language_settings.get(language, self.language_settings['ru'])
                normal_pause_range = lang_settings['pause_thresholds']
                
                if normal_pause_range[0] <= avg_pause_duration <= normal_pause_range[1]:
                    pause_quality = "хорошо"
                elif avg_pause_duration < normal_pause_range[0]:
                    pause_quality = "слишком короткие"
                else:
                    pause_quality = "слишком длинные"
            else:
                avg_pause_duration = 0
                pause_frequency = 0
                pause_quality = "пауз не обнаружено"
            
            return {
                "pause_frequency": int(pause_frequency),
                "average_pause_duration": float(avg_pause_duration),
                "pause_quality": pause_quality,
                "total_pauses": len(pauses)
            }
            
        except Exception as e:
            logger.error(f"Pause analysis failed: {e}")
            return {
                "pause_frequency": 5,
                "average_pause_duration": 0.5,
                "pause_quality": "нормально",
                "total_pauses": 0
            }
    
    def _analyze_audio_energy(self, y: np.ndarray) -> Dict[str, Any]:
        """Анализ энергии и громкости аудио"""
        try:
            # RMS энергия
            rms_energy = librosa.feature.rms(y=y)[0]
            average_energy = float(np.mean(rms_energy))
            energy_variation = float(np.std(rms_energy))
            
            # Спектральная энергия
            spectral_rolloff = librosa.feature.spectral_rolloff(y=y)[0]
            avg_spectral_rolloff = float(np.mean(spectral_rolloff))
            
            # Оценка динамического диапазона
            dynamic_range = float(np.max(rms_energy) - np.min(rms_energy))
            
            return {
                "average_energy": average_energy,
                "energy_variation": energy_variation,
                "dynamic_range": dynamic_range,
                "spectral_rolloff": avg_spectral_rolloff
            }
            
        except Exception as e:
            logger.error(f"Audio energy analysis failed: {e}")
            return {
                "average_energy": 0.5,
                "energy_variation": 0.1,
                "dynamic_range": 0.3,
                "spectral_rolloff": 2000.0
            }
    
    async def _analyze_linguistic_features(self, transcript_data: Dict, language: str) -> Dict[str, Any]:
        """Лингвистический анализ транскрипта"""
        try:
            transcript = transcript_data.get("transcript", "")
            if not transcript:
                return {
                    "vocabulary_richness": 0,
                    "grammar_complexity": 1,
                    "sentence_structure": "неопределено"
                }
            
            words = transcript.lower().split()
            
            # Анализ словарного запаса
            unique_words = set(words)
            vocabulary_richness = len(unique_words) / len(words) if words else 0
            
            # Анализ сложности предложений
            sentences = transcript.split('.')
            sentences = [s.strip() for s in sentences if s.strip()]
            
            if sentences:
                avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)
                grammar_complexity = min(10, max(1, int(avg_sentence_length / 2)))
            else:
                grammar_complexity = 1
            
            # Анализ структуры речи
            if grammar_complexity >= 8:
                sentence_structure = "сложная"
            elif grammar_complexity >= 5:
                sentence_structure = "средняя"
            else:
                sentence_structure = "простая"
            
            # Анализ слов-паразитов (для русского языка)
            if language == 'ru':
                filler_words = ['эм', 'эээ', 'ммм', 'это', 'ну', 'как бы', 'типа', 'в общем']
                filler_count = sum(words.count(word) for word in filler_words)
                filler_ratio = filler_count / len(words) if words else 0
            else:
                filler_words = ['um', 'uh', 'er', 'like', 'you know', 'actually']
                filler_count = sum(words.count(word) for word in filler_words)
                filler_ratio = filler_count / len(words) if words else 0
            
            return {
                "vocabulary_richness": round(vocabulary_richness, 3),
                "grammar_complexity": grammar_complexity,
                "sentence_structure": sentence_structure,
                "filler_words_ratio": round(filler_ratio, 3),
                "average_sentence_length": avg_sentence_length if sentences else 0
            }
            
        except Exception as e:
            logger.error(f"Linguistic analysis failed: {e}")
            return {
                "vocabulary_richness": 0.5,
                "grammar_complexity": 5,
                "sentence_structure": "средняя",
                "filler_words_ratio": 0.05,
                "average_sentence_length": 8.0
            }
    
    async def _assess_audio_quality(self, audio_path: str) -> int:
        """Оценка качества аудио (1-10)"""
        try:
            y, sr = librosa.load(audio_path, sr=16000)
            
            quality_score = 5  # Базовая оценка
            
            # Проверка уровня шума
            rms = librosa.feature.rms(y=y)[0]
            noise_level = np.percentile(rms, 10)  # Нижние 10% как показатель шума
            
            if noise_level < 0.01:
                quality_score += 2  # Низкий уровень шума
            elif noise_level > 0.05:
                quality_score -= 1  # Высокий уровень шума
            
            # Проверка динамического диапазона
            dynamic_range = np.max(rms) - np.min(rms)
            if dynamic_range > 0.3:
                quality_score += 1  # Хороший динамический диапазон
            elif dynamic_range < 0.1:
                quality_score -= 1  # Плохой динамический диапазон
            
            # Проверка частотного спектра
            spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
            avg_centroid = np.mean(spectral_centroid)
            
            if 1000 <= avg_centroid <= 4000:  # Оптимальный диапазон для речи
                quality_score += 1
            
            return max(1, min(10, quality_score))
            
        except Exception as e:
            logger.error(f"Audio quality assessment failed: {e}")
            return 5
    
    async def _cleanup_temp_files(self, *file_paths: str):
        """Очистка временных файлов"""
        for file_path in file_paths:
            try:
                if file_path and os.path.exists(file_path):
                    os.unlink(file_path)
                    logger.info(f"Cleaned up temp file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file {file_path}: {e}")


# Фабрика для создания экземпляра
def create_audio_processor() -> AudioProcessor:
    """Создание экземпляра аудио процессора"""
    return AudioProcessor()
