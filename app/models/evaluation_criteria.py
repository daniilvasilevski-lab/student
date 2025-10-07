"""
Расширенная модель критериев оценки интервью студентов
10 критериев по 10 баллов каждый
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from enum import Enum


class EvaluationCriteria(str, Enum):
    """10 критериев оценки интервью"""
    COMMUNICATION_SKILLS = "communication_skills"  # Коммуникативные навыки
    MOTIVATION_LEARNING = "motivation_learning"    # Мотивация к обучению  
    PROFESSIONAL_SKILLS = "professional_skills"    # Профессиональные навыки
    ANALYTICAL_THINKING = "analytical_thinking"    # Аналитическое мышление
    UNCONVENTIONAL_THINKING = "unconventional_thinking"  # Лидерский потенциал
    TEAMWORK_ABILITY = "teamwork_ability"         # Способность к командной работе
    STRESS_RESISTANCE = "stress_resistance"       # Стрессоустойчивость
    ADAPTABILITY = "adaptability"                 # Адаптивность
    CREATIVITY_INNOVATION = "creativity_innovation" # Креативность и инновационность
    OVERALL_IMPRESSION = "overall_impression"     # Общее впечатление


class CriteriaWeights(BaseModel):
    """Веса критериев для разных позиций"""
    communication_skills: float = 1.0
    motivation_learning: float = 1.0
    professional_skills: float = 1.0
    analytical_thinking: float = 1.0
    leadership_potential: float = 0.8
    teamwork_ability: float = 1.0
    stress_resistance: float = 0.9
    adaptability: float = 0.9
    creativity_innovation: float = 0.8
    overall_impression: float = 1.0


class CriteriaDescription(BaseModel):
    """Описание критерия оценки"""
    name: str
    description: str
    key_indicators: List[str]
    verbal_aspects: List[str]
    non_verbal_aspects: List[str]


class EvaluationScore(BaseModel):
    """Оценка по одному критерию"""
    criterion: EvaluationCriteria
    score: int = Field(..., ge=1, le=10, description="Оценка от 1 до 10")
    verbal_score: int = Field(..., ge=1, le=5, description="Вербальная оценка 1-5")
    non_verbal_score: int = Field(..., ge=1, le=5, description="Невербальная оценка 1-5")
    explanation: str = Field(..., description="Обоснование оценки")
    key_observations: List[str] = Field(..., description="Ключевые наблюдения")
    specific_examples: List[str] = Field(..., description="Конкретные примеры из интервью")
    formatted_evaluation: str = Field(..., description="Форматированная оценка X/10 + объяснение с примерами")


class InterviewAnalysis(BaseModel):
    """Полный анализ интервью"""
    candidate_id: str
    candidate_name: str
    interview_duration: int  # в секундах
    
    # Индивидуальные оценки по критериям
    scores: Dict[EvaluationCriteria, EvaluationScore]
    
    # Технический анализ
    audio_quality: int = Field(..., ge=1, le=10)
    video_quality: int = Field(..., ge=1, le=10)
    
    # Невербальный анализ
    emotion_analysis: Dict[str, float]  # радость, грусть, нейтральность и т.д.
    eye_contact_percentage: float
    gesture_frequency: int
    posture_confidence: int = Field(..., ge=1, le=10)
    
    # Вербальный анализ
    speech_pace: str  # медленный, нормальный, быстрый
    vocabulary_richness: int = Field(..., ge=1, le=10)
    grammar_quality: int = Field(..., ge=1, le=10)
    answer_structure: int = Field(..., ge=1, le=10)
    
    # Итоговые показатели
    total_score: int = Field(..., ge=10, le=100)
    weighted_score: float
    recommendation: str
    detailed_feedback: str
    
    # Метаданные
    analysis_timestamp: str
    ai_model_version: str


# Подробные описания критериев
CRITERIA_DESCRIPTIONS = {
    EvaluationCriteria.COMMUNICATION_SKILLS: CriteriaDescription(
        name="Коммуникативные навыки",
        description="Способность четко и эффективно общаться",
        key_indicators=[
            "Ясность речи",
            "Структурированность ответов", 
            "Способность слушать",
            "Понимание вопросов"
        ],
        verbal_aspects=[
            "Четкость произношения",
            "Громкость и темп речи",
            "Использование профессиональной лексики",
            "Грамматическая правильность"
        ],
        non_verbal_aspects=[
            "Зрительный контакт",
            "Мимика и выражение лица",
            "Позы и жесты",
            "Уверенность в поведении"
        ]
    ),
    
    EvaluationCriteria.MOTIVATION_LEARNING: CriteriaDescription(
        name="Мотивация к обучению",
        description="Желание развиваться и учиться новому",
        key_indicators=[
            "Интерес к саморазвитию",
            "Готовность к вызовам",
            "Понимание карьерных целей",
            "Энтузиазм в ответах"
        ],
        verbal_aspects=[
            "Упоминание курсов и обучения",
            "Вопросы о развитии",
            "Планы на будущее",
            "Энергичность в речи"
        ],
        non_verbal_aspects=[
            "Заинтересованность в глазах",
            "Активные жесты",
            "Прямая осанка",
            "Эмоциональная включенность"
        ]
    ),
    
    EvaluationCriteria.PROFESSIONAL_SKILLS: CriteriaDescription(
        name="Профессиональные навыки",
        description="Технические и прикладные знания в области",
        key_indicators=[
            "Знание предметной области",
            "Практический опыт",
            "Технические навыки",
            "Понимание трендов"
        ],
        verbal_aspects=[
            "Использование терминологии",
            "Примеры из практики",
            "Глубина ответов",
            "Конкретные достижения"
        ],
        non_verbal_aspects=[
            "Уверенность при ответах",
            "Отсутствие колебаний",
            "Четкие жесты",
            "Прямой взгляд"
        ]
    ),
    
    EvaluationCriteria.ANALYTICAL_THINKING: CriteriaDescription(
        name="Аналитическое мышление",
        description="Способность к логическому анализу и решению проблем",
        key_indicators=[
            "Логичность рассуждений",
            "Способность к декомпозиции",
            "Причинно-следственные связи",
            "Критическое мышление"
        ],
        verbal_aspects=[
            "Структура ответов",
            "Логические связки",
            "Аргументация",
            "Примеры решений"
        ],
        non_verbal_aspects=[
            "Паузы для размышления",
            "Сосредоточенность",
            "Жесты объяснения",
            "Внимательный взгляд"
        ]
    ),
    
    EvaluationCriteria.UNCONVENTIONAL_THINKING: CriteriaDescription(
        name="Умение нестандартно мыслить",
        description="Способность к креативному, нетривиальному подходу к решению задач",
        key_indicators=[
            "Оригинальность решений",
            "Нестандартный подход",
            "Выход за рамки шаблонов",
            "Инновационное мышление"
        ],
        verbal_aspects=[
            "Необычные идеи и решения",
            "Креативные аналогии",
            "Нестандартные примеры",
            "Инновационные предложения"
        ],
        non_verbal_aspects=[
            "Живая, выразительная мимика",
            "Творческие жесты",
            "Заинтересованный взгляд",
            "Динамичность движений"
        ]
    ),
    
    EvaluationCriteria.TEAMWORK_ABILITY: CriteriaDescription(
        name="Способность к командной работе",
        description="Умение эффективно работать в команде",
        key_indicators=[
            "Опыт командной работы",
            "Коммуникация в группе",
            "Поддержка коллег",
            "Конструктивность"
        ],
        verbal_aspects=[
            "Примеры совместной работы",
            "Использование \"мы\" вместо \"я\"",
            "Упоминание коллег",
            "Готовность к компромиссам"
        ],
        non_verbal_aspects=[
            "Открытые жесты",
            "Приветливая мимика",
            "Внимательность к собеседнику",
            "Доброжелательность"
        ]
    ),
    
    EvaluationCriteria.STRESS_RESISTANCE: CriteriaDescription(
        name="Стрессоустойчивость",
        description="Способность эффективно работать под давлением",
        key_indicators=[
            "Спокойствие в сложных ситуациях",
            "Управление эмоциями",
            "Работа под давлением",
            "Восстановление после неудач"
        ],
        verbal_aspects=[
            "Ровный тон голоса",
            "Отсутствие речевых сбоев",
            "Спокойные ответы",
            "Примеры преодоления трудностей"
        ],
        non_verbal_aspects=[
            "Расслабленная поза",
            "Контроль мимики",
            "Отсутствие тревожных жестов",
            "Ровное дыхание"
        ]
    ),
    
    EvaluationCriteria.ADAPTABILITY: CriteriaDescription(
        name="Адаптивность",
        description="Гибкость и способность к изменениям",
        key_indicators=[
            "Открытость к изменениям",
            "Быстрота обучения",
            "Гибкость мышления",
            "Адаптация к новому"
        ],
        verbal_aspects=[
            "Готовность к переменам",
            "Примеры адаптации",
            "Позитивное отношение к новому",
            "Быстрота переключения тем"
        ],
        non_verbal_aspects=[
            "Открытые жесты",
            "Гибкость движений",
            "Быстрая реакция",
            "Заинтересованность"
        ]
    ),
    
    EvaluationCriteria.CREATIVITY_INNOVATION: CriteriaDescription(
        name="Креативность и инновационность", 
        description="Способность к творческому мышлению и нестандартным решениям",
        key_indicators=[
            "Нестандартные решения",
            "Творческий подход",
            "Инновационные идеи",
            "Оригинальность мышления"
        ],
        verbal_aspects=[
            "Необычные примеры",
            "Креативные решения",
            "Новые идеи",
            "Нестандартные подходы"
        ],
        non_verbal_aspects=[
            "Живая мимика",
            "Выразительные жесты",
            "Энтузиазм в глазах",
            "Динамичность"
        ]
    ),
    
    EvaluationCriteria.OVERALL_IMPRESSION: CriteriaDescription(
        name="Общее впечатление",
        description="Целостная оценка кандидата как потенциального сотрудника",
        key_indicators=[
            "Профессионализм",
            "Личностная зрелость",
            "Соответствие корпоративной культуре",
            "Потенциал развития"
        ],
        verbal_aspects=[
            "Общий уровень ответов",
            "Профессиональность речи",
            "Соответствие ожиданиям",
            "Впечатление от диалога"
        ],
        non_verbal_aspects=[
            "Общая презентабельность",
            "Профессиональный вид",
            "Уверенность в себе",
            "Харизма и обаяние"
        ]
    )
}