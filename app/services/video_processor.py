"""
Сервис для обработки видео с интервью
Извлекает аудио, анализирует эмоции, жесты и позы
"""

import cv2
import numpy as np
import logging
import asyncio
import tempfile
import os
from typing import Dict, List, Any, Tuple, Optional
import aiohttp
import aiofiles
from urllib.parse import urlparse
import subprocess
import math
from datetime import datetime, timedelta

# Computer Vision
import mediapipe as mp
from deepface import DeepFace
import face_recognition

logger = logging.getLogger(__name__)


class VideoProcessor:
    """Процессор для анализа видео интервью"""
    
    def __init__(self):
        # Инициализация MediaPipe
        self.mp_pose = mp.solutions.pose
        self.mp_face_mesh = mp.solutions.face_mesh
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        
        # Инициализация детекторов
        self.pose_detector = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            enable_segmentation=False,
            min_detection_confidence=0.5
        )
        
        self.face_mesh_detector = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5
        )
        
        self.hands_detector = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.5
        )
        
    async def process_video(self, video_url: str) -> Dict[str, Any]:
        """
        Основной метод обработки видео
        
        Args:
            video_url: URL видео для анализа
            
        Returns:
            Dict с результатами анализа видео
        """
        logger.info(f"Starting video processing for URL: {video_url}")
        
        try:
            # 1. Скачивание видео
            video_path = await self._download_video(video_url)
            
            # 2. Извлечение информации о видео
            video_info = await self._get_video_info(video_path)
            
            # 3. Анализ видео
            analysis_results = await self._analyze_video_content(video_path, video_info)
            
            # 4. Очистка временных файлов
            await self._cleanup_temp_files(video_path)
            
            logger.info("Video processing completed successfully")
            return analysis_results
            
        except Exception as e:
            logger.error(f"Video processing failed: {str(e)}")
            raise e
    
    async def _download_video(self, video_url: str) -> str:
        """Скачивание видео во временный файл"""
        try:
            # Проверяем, что это валидный URL
            parsed_url = urlparse(video_url)
            if not parsed_url.scheme or not parsed_url.netloc:
                raise ValueError(f"Invalid video URL: {video_url}")
            
            # Создаем временный файл
            temp_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
            temp_path = temp_file.name
            temp_file.close()
            
            # Скачиваем видео
            timeout = aiohttp.ClientTimeout(total=300)  # 5 минут таймаут
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(video_url) as response:
                    if response.status != 200:
                        raise ValueError(f"Failed to download video: HTTP {response.status}")
                    
                    # Проверяем размер файла (лимит 100MB)
                    content_length = response.headers.get('content-length')
                    if content_length and int(content_length) > 100 * 1024 * 1024:
                        raise ValueError("Video file too large (>100MB)")
                    
                    async with aiofiles.open(temp_path, 'wb') as temp_file:
                        async for chunk in response.content.iter_chunked(8192):
                            await temp_file.write(chunk)
            
            logger.info(f"Video downloaded to: {temp_path}")
            return temp_path
            
        except Exception as e:
            logger.error(f"Failed to download video from {video_url}: {e}")
            raise e
    
    async def _get_video_info(self, video_path: str) -> Dict[str, Any]:
        """Получение информации о видео"""
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError(f"Failed to open video file: {video_path}")
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            duration = frame_count / fps if fps > 0 else 0
            
            cap.release()
            
            video_info = {
                "duration": duration,
                "fps": fps,
                "frame_count": frame_count,
                "width": width,
                "height": height,
                "aspect_ratio": width / height if height > 0 else 1.0,
                "video_quality": self._assess_video_quality(width, height, fps)
            }
            
            logger.info(f"Video info extracted: {video_info}")
            return video_info
            
        except Exception as e:
            logger.error(f"Failed to get video info: {e}")
            raise e
    
    def _assess_video_quality(self, width: int, height: int, fps: float) -> int:
        """Оценка качества видео от 1 до 10"""
        quality_score = 5  # Базовая оценка
        
        # Оценка разрешения
        pixels = width * height
        if pixels >= 1920 * 1080:  # Full HD+
            quality_score += 2
        elif pixels >= 1280 * 720:  # HD
            quality_score += 1
        elif pixels < 640 * 480:  # Низкое разрешение
            quality_score -= 2
        
        # Оценка FPS
        if fps >= 30:
            quality_score += 1
        elif fps < 15:
            quality_score -= 1
        
        return max(1, min(10, quality_score))
    
    async def _analyze_video_content(self, video_path: str, video_info: Dict) -> Dict[str, Any]:
        """Анализ содержимого видео"""
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError(f"Failed to open video for analysis: {video_path}")
            
            # Инициализируем аккумуляторы данных
            analysis_data = {
                "emotions": [],
                "poses": [],
                "hand_gestures": [],
                "eye_contact_frames": [],
                "frame_count": 0,
                "processed_frames": 0
            }
            
            fps = video_info["fps"]
            frame_interval = max(1, int(fps / 2))  # Анализируем каждые 0.5 секунды
            
            frame_number = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Обрабатываем только каждый N-й кадр для оптимизации
                if frame_number % frame_interval == 0:
                    await self._process_frame(frame, frame_number, fps, analysis_data)
                    analysis_data["processed_frames"] += 1
                
                frame_number += 1
                analysis_data["frame_count"] = frame_number
            
            cap.release()
            
            # Агрегируем результаты
            aggregated_results = self._aggregate_analysis_results(analysis_data, video_info)
            
            logger.info(f"Video content analysis completed. Processed {analysis_data['processed_frames']} frames")
            return aggregated_results
            
        except Exception as e:
            logger.error(f"Video content analysis failed: {e}")
            raise e
    
    async def _process_frame(self, frame: np.ndarray, frame_number: int, fps: float, analysis_data: Dict):
        """Обработка одного кадра"""
        try:
            timestamp = frame_number / fps
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # 1. Анализ эмоций
            try:
                emotions = await self._analyze_emotions(rgb_frame)
                if emotions:
                    emotions["timestamp"] = timestamp
                    analysis_data["emotions"].append(emotions)
            except Exception as e:
                logger.warning(f"Emotion analysis failed for frame {frame_number}: {e}")
            
            # 2. Анализ позы
            try:
                pose_data = await self._analyze_pose(rgb_frame)
                if pose_data:
                    pose_data["timestamp"] = timestamp
                    analysis_data["poses"].append(pose_data)
            except Exception as e:
                logger.warning(f"Pose analysis failed for frame {frame_number}: {e}")
            
            # 3. Анализ жестов рук
            try:
                hand_data = await self._analyze_hand_gestures(rgb_frame)
                if hand_data:
                    hand_data["timestamp"] = timestamp
                    analysis_data["hand_gestures"].append(hand_data)
            except Exception as e:
                logger.warning(f"Hand analysis failed for frame {frame_number}: {e}")
            
            # 4. Анализ зрительного контакта
            try:
                eye_contact = await self._analyze_eye_contact(rgb_frame)
                if eye_contact is not None:
                    analysis_data["eye_contact_frames"].append({
                        "timestamp": timestamp,
                        "eye_contact": eye_contact
                    })
            except Exception as e:
                logger.warning(f"Eye contact analysis failed for frame {frame_number}: {e}")
                
        except Exception as e:
            logger.warning(f"Frame processing failed for frame {frame_number}: {e}")
    
    async def _analyze_emotions(self, frame: np.ndarray) -> Optional[Dict]:
        """Анализ эмоций на кадре"""
        try:
            # Используем DeepFace для анализа эмоций
            result = DeepFace.analyze(
                img_path=frame,
                actions=['emotion'],
                enforce_detection=False,
                silent=True
            )
            
            if isinstance(result, list) and len(result) > 0:
                emotion_data = result[0].get('emotion', {})
                return {
                    "dominant_emotion": result[0].get('dominant_emotion', 'neutral'),
                    "emotion_scores": emotion_data,
                    "confidence": max(emotion_data.values()) if emotion_data else 0.0
                }
            
            return None
            
        except Exception as e:
            logger.debug(f"Emotion analysis failed: {e}")
            return None
    
    async def _analyze_pose(self, frame: np.ndarray) -> Optional[Dict]:
        """Анализ позы тела"""
        try:
            results = self.pose_detector.process(frame)
            
            if results.pose_landmarks:
                landmarks = results.pose_landmarks.landmark
                
                # Извлекаем ключевые точки
                nose = landmarks[self.mp_pose.PoseLandmark.NOSE]
                left_shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER]
                right_shoulder = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]
                
                # Вычисляем уверенность позы
                posture_confidence = self._calculate_posture_confidence(
                    nose, left_shoulder, right_shoulder
                )
                
                # Определяем наклон головы
                head_tilt = self._calculate_head_tilt(nose, left_shoulder, right_shoulder)
                
                return {
                    "posture_confidence": posture_confidence,
                    "head_tilt": head_tilt,
                    "shoulders_level": abs(left_shoulder.y - right_shoulder.y) < 0.05,
                    "pose_detected": True
                }
            
            return {"pose_detected": False}
            
        except Exception as e:
            logger.debug(f"Pose analysis failed: {e}")
            return None
    
    def _calculate_posture_confidence(self, nose, left_shoulder, right_shoulder) -> int:
        """Вычисление уверенности позы (1-10)"""
        try:
            # Проверяем прямоту спины (плечи на одном уровне)
            shoulder_diff = abs(left_shoulder.y - right_shoulder.y)
            
            # Проверяем центрированность головы
            shoulder_center_x = (left_shoulder.x + right_shoulder.x) / 2
            head_center_offset = abs(nose.x - shoulder_center_x)
            
            # Базовая оценка
            confidence = 7
            
            # Штрафы за плохую позу
            if shoulder_diff > 0.05:  # Плечи неровные
                confidence -= 2
            if head_center_offset > 0.1:  # Голова сильно смещена
                confidence -= 1
            
            # Бонусы за хорошую позу
            if shoulder_diff < 0.02 and head_center_offset < 0.05:
                confidence += 1
                
            return max(1, min(10, confidence))
            
        except Exception:
            return 5  # Средняя оценка при ошибке
    
    def _calculate_head_tilt(self, nose, left_shoulder, right_shoulder) -> float:
        """Вычисление наклона головы в градусах"""
        try:
            shoulder_center_x = (left_shoulder.x + right_shoulder.x) / 2
            shoulder_center_y = (left_shoulder.y + right_shoulder.y) / 2
            
            # Вектор от центра плеч к носу
            dx = nose.x - shoulder_center_x
            dy = nose.y - shoulder_center_y
            
            # Угол в градусах
            angle = math.degrees(math.atan2(dx, dy))
            return angle
            
        except Exception:
            return 0.0
    
    async def _analyze_hand_gestures(self, frame: np.ndarray) -> Optional[Dict]:
        """Анализ жестов рук"""
        try:
            results = self.hands_detector.process(frame)
            
            gesture_data = {
                "hands_detected": 0,
                "gesture_activity": 0,  # 0-10 шкала активности
                "hand_positions": []
            }
            
            if results.multi_hand_landmarks:
                gesture_data["hands_detected"] = len(results.multi_hand_landmarks)
                
                for hand_landmarks in results.multi_hand_landmarks:
                    # Вычисляем активность жестов по движению кистей
                    wrist = hand_landmarks.landmark[0]  # Запястье
                    middle_finger_tip = hand_landmarks.landmark[12]  # Кончик среднего пальца
                    
                    # Расстояние от запястья до кончика пальца (мера раскрытости руки)
                    hand_openness = math.sqrt(
                        (wrist.x - middle_finger_tip.x) ** 2 + 
                        (wrist.y - middle_finger_tip.y) ** 2
                    )
                    
                    gesture_data["hand_positions"].append({
                        "wrist_position": (wrist.x, wrist.y),
                        "openness": hand_openness
                    })
                
                # Оценка активности жестов
                if gesture_data["hands_detected"] > 0:
                    gesture_data["gesture_activity"] = min(10, gesture_data["hands_detected"] * 3)
            
            return gesture_data
            
        except Exception as e:
            logger.debug(f"Hand gesture analysis failed: {e}")
            return None
    
    async def _analyze_eye_contact(self, frame: np.ndarray) -> Optional[bool]:
        """Анализ зрительного контакта"""
        try:
            results = self.face_mesh_detector.process(frame)
            
            if results.multi_face_landmarks:
                face_landmarks = results.multi_face_landmarks[0]
                
                # Анализируем направление взгляда по положению зрачков
                # Используем ключевые точки глаз
                left_eye_center = face_landmarks.landmark[468]  # Центр левого глаза
                right_eye_center = face_landmarks.landmark[473]  # Центр правого глаза
                nose_tip = face_landmarks.landmark[1]  # Кончик носа
                
                # Простая эвристика: если глаза смотрят примерно в центр камеры
                eye_center_x = (left_eye_center.x + right_eye_center.x) / 2
                eye_center_y = (left_eye_center.y + right_eye_center.y) / 2
                
                # Зрительный контакт, если взгляд направлен в центральную область (±20%)
                center_threshold = 0.2
                is_looking_at_camera = (
                    abs(eye_center_x - 0.5) < center_threshold and
                    abs(eye_center_y - 0.5) < center_threshold
                )
                
                return is_looking_at_camera
            
            return False
            
        except Exception as e:
            logger.debug(f"Eye contact analysis failed: {e}")
            return None
    
    def _aggregate_analysis_results(self, analysis_data: Dict, video_info: Dict) -> Dict[str, Any]:
        """Агрегация результатов анализа"""
        try:
            duration = video_info["duration"]
            
            # Агрегация эмоций
            emotion_analysis = self._aggregate_emotions(analysis_data["emotions"])
            
            # Агрегация позы
            posture_analysis = self._aggregate_posture(analysis_data["poses"])
            
            # Агрегация жестов
            gesture_analysis = self._aggregate_gestures(analysis_data["hand_gestures"])
            
            # Агрегация зрительного контакта
            eye_contact_analysis = self._aggregate_eye_contact(analysis_data["eye_contact_frames"])
            
            # Итоговый результат
            result = {
                "duration": duration,
                "video_quality": video_info["video_quality"],
                "emotion_analysis": emotion_analysis,
                "posture_confidence": posture_analysis["average_confidence"],
                "gesture_frequency": gesture_analysis["average_activity"],
                "eye_contact_percentage": eye_contact_analysis["percentage"],
                "processing_stats": {
                    "total_frames": analysis_data["frame_count"],
                    "processed_frames": analysis_data["processed_frames"],
                    "processing_ratio": analysis_data["processed_frames"] / max(1, analysis_data["frame_count"])
                }
            }
            
            logger.info(f"Analysis aggregation completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to aggregate analysis results: {e}")
            raise e
    
    def _aggregate_emotions(self, emotions: List[Dict]) -> Dict[str, float]:
        """Агрегация эмоций"""
        if not emotions:
            return {"neutral": 100.0}
        
        emotion_totals = {}
        for emotion_data in emotions:
            scores = emotion_data.get("emotion_scores", {})
            for emotion, score in scores.items():
                emotion_totals[emotion] = emotion_totals.get(emotion, 0) + score
        
        # Нормализация
        total_count = len(emotions)
        emotion_averages = {
            emotion: total / total_count 
            for emotion, total in emotion_totals.items()
        }
        
        return emotion_averages
    
    def _aggregate_posture(self, poses: List[Dict]) -> Dict[str, Any]:
        """Агрегация данных позы"""
        if not poses:
            return {"average_confidence": 5, "pose_stability": 5}
        
        confidences = [
            pose.get("posture_confidence", 5) 
            for pose in poses if pose.get("pose_detected", False)
        ]
        
        if not confidences:
            return {"average_confidence": 5, "pose_stability": 5}
        
        avg_confidence = sum(confidences) / len(confidences)
        
        # Стабильность позы (низкое стандартное отклонение = высокая стабильность)
        if len(confidences) > 1:
            variance = sum((x - avg_confidence) ** 2 for x in confidences) / len(confidences)
            stability = max(1, 10 - int(variance))
        else:
            stability = avg_confidence
        
        return {
            "average_confidence": int(avg_confidence),
            "pose_stability": stability
        }
    
    def _aggregate_gestures(self, gestures: List[Dict]) -> Dict[str, Any]:
        """Агрегация данных жестов"""
        if not gestures:
            return {"average_activity": 0, "gesture_variety": 0}
        
        activities = [g.get("gesture_activity", 0) for g in gestures]
        avg_activity = sum(activities) / len(activities) if activities else 0
        
        # Разнообразие жестов (количество различных позиций рук)
        hands_detected_frames = len([g for g in gestures if g.get("hands_detected", 0) > 0])
        gesture_variety = min(10, int((hands_detected_frames / len(gestures)) * 10)) if gestures else 0
        
        return {
            "average_activity": int(avg_activity),
            "gesture_variety": gesture_variety
        }
    
    def _aggregate_eye_contact(self, eye_contact_frames: List[Dict]) -> Dict[str, Any]:
        """Агрегация данных зрительного контакта"""
        if not eye_contact_frames:
            return {"percentage": 0.0, "consistency": 0}
        
        positive_frames = len([
            frame for frame in eye_contact_frames 
            if frame.get("eye_contact", False)
        ])
        
        percentage = (positive_frames / len(eye_contact_frames)) * 100
        
        # Консистентность (равномерность зрительного контакта)
        consistency = min(10, int(percentage / 10))
        
        return {
            "percentage": round(percentage, 1),
            "consistency": consistency
        }
    
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
def create_video_processor() -> VideoProcessor:
    """Создание экземпляра видео процессора"""
    return VideoProcessor()
