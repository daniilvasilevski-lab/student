"""
Конфигурация промптов для анализаторов с поддержкой мультиязычности
"""

from typing import Dict

class PromptConfig:
    """Конфигурация промптов для разных языков и анализаторов"""
    
    # Системные промпты для разных анализаторов
    SYSTEM_PROMPTS = {
        "integrated_analyzer": {
            "ru": "Ты эксперт-психолог и HR-специалист с 15+ лет опыта анализа интервью. Анализируешь целостно, учитывая все модальности в комплексе. Отвечай НА РУССКОМ ЯЗЫКЕ.",
            "en": "You are an expert psychologist and HR specialist with 15+ years of interview analysis experience. You analyze holistically, considering all modalities in complex. Respond IN ENGLISH.",
            "pl": "Jesteś ekspertem psychologiem i specjalistą HR z ponad 15-letnim doświadczeniem w analizie rozmów kwalifikacyjnych. Analizujesz holistycznie, uwzględniając wszystkie modalności kompleksowo. Odpowiadaj PO POLSKU."
        },
        
        "temporal_analyzer": {
            "ru": "Ты эксперт-психолог с 20+ лет опыта анализа динамики поведения в интервью. Фокусируешься на изменениях во времени, а не на статических оценках. Отвечай НА РУССКОМ ЯЗЫКЕ.",
            "en": "You are an expert psychologist with 20+ years of experience analyzing behavioral dynamics in interviews. You focus on changes over time, not static assessments. Respond IN ENGLISH.", 
            "pl": "Jesteś ekspertem psychologiem z ponad 20-letnim doświadczeniem w analizie dynamiki zachowań podczas rozmów kwalifikacyjnych. Koncentrujesz się na zmianach w czasie, a nie na statycznych ocenach. Odpowiadaj PO POLSKU."
        },
        
        "cv_analyzer": {
            "ru": "Ты профессиональный HR-аналитик, специализирующийся на IT-резюме. Анализируй резюме объективно и давай конструктивную обратную связь. Отвечай НА РУССКОМ ЯЗЫКЕ.",
            "en": "You are a professional HR analyst specializing in IT resumes. Analyze resumes objectively and provide constructive feedback. Respond IN ENGLISH.",
            "pl": "Jesteś profesjonalnym analitykiem HR specjalizującym się w CV IT. Analizuj CV obiektywnie i udzielaj konstruktywnych informacji zwrotnych. Odpowiadaj PO POLSKU."
        },
        
        "questions_analyzer": {
            "ru": "Ты эксперт по структуре интервью и классификации вопросов. Анализируй типы вопросов и их структуру профессионально. Отвечай НА РУССКОМ ЯЗЫКЕ.",
            "en": "You are an expert in interview structure and question classification. Analyze question types and their structure professionally. Respond IN ENGLISH.",
            "pl": "Jesteś ekspertem w strukturze rozmów kwalifikacyjnych i klasyfikacji pytań. Analizuj typy pytań i ich strukturę profesjonalnie. Odpowiadaj PO POLSKU."
        },
        
        "question_classifier": {
            "ru": "Ты эксперт по анализу интервью. Классифицируй типы вопросов точно и кратко. Отвечай НА РУССКОМ ЯЗЫКЕ.",
            "en": "You are an interview analysis expert. Classify question types accurately and concisely. Respond IN ENGLISH.", 
            "pl": "Jesteś ekspertem w analizie rozmów kwalifikacyjnych. Klasyfikuj typy pytań dokładnie i zwięźle. Odpowiadaj PO POLSKU."
        }
    }
    
    @staticmethod
    def get_system_prompt(analyzer_type: str, language: str = "ru") -> str:
        """
        Получение системного промпта для конкретного анализатора и языка
        
        Args:
            analyzer_type: Тип анализатора
            language: Код языка ('ru', 'en', 'pl')
            
        Returns:
            str: Системный промпт
        """
        prompts = PromptConfig.SYSTEM_PROMPTS.get(analyzer_type, {})
        return prompts.get(language, prompts.get("ru", ""))
    
    @staticmethod
    def detect_language_from_text(text: str) -> str:
        """
        Определение языка текста
        
        Args:
            text: Текст для анализа
            
        Returns:
            str: Код языка ('ru', 'en', 'pl')
        """
        import re
        
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
        
        # Проверяем наличие кириллицы
        has_cyrillic = bool(re.search(r'[а-яё]', text_lower))
        if has_cyrillic:
            russian_score += 3
            
        # Проверяем польские специальные символы
        has_polish = bool(re.search(r'[ąćęłńóśźż]', text_lower))
        if has_polish:
            polish_score += 4
        
        # Определяем язык по наибольшему счету
        scores = {'pl': polish_score, 'ru': russian_score, 'en': english_score}
        detected_language = max(scores, key=scores.get)
        
        # Если все счета равны 0, по умолчанию русский (наша основная аудитория)
        return detected_language if max(scores.values()) > 0 else 'ru'

    # Шаблоны для различных типов анализа
    ANALYSIS_TEMPLATES = {
        "criteria_evaluation": {
            "ru": """
Оценивай каждый критерий по шкале от 1 до 10 и давай развернутое объяснение с конкретными примерами из интервью.

Критерии оценки:
1. Коммуникативные навыки - четкость речи, структурированность изложения
2. Мотивация к обучению - желание развиваться, изучать новое
3. Профессиональные навыки - технические знания, опыт работы
4. Аналитическое мышление - способность анализировать и решать задачи
5. Нестандартное мышление - креативность, способность мыслить вне шаблонов
6. Командная работа - навыки взаимодействия в коллективе
7. Стрессоустойчивость - способность работать под давлением
8. Адаптивность - гибкость, способность к изменениям
9. Креативность - творческий подход к решению задач
10. Общее впечатление - итоговая оценка кандидата

Формат ответа: Для каждого критерия укажи оценку/10 + подробное объяснение с примерами.
""",
            "en": """
Evaluate each criterion on a scale from 1 to 10 and provide detailed explanations with specific examples from the interview.

Evaluation criteria:
1. Communication Skills - speech clarity, structured presentation
2. Motivation & Learning - desire to develop, learn new things
3. Professional Skills - technical knowledge, work experience
4. Analytical Thinking - ability to analyze and solve problems
5. Unconventional Thinking - creativity, ability to think outside the box
6. Teamwork Ability - skills in team collaboration
7. Stress Resistance - ability to work under pressure
8. Adaptability - flexibility, ability to adapt to changes
9. Creativity & Innovation - creative approach to problem-solving
10. Overall Impression - final assessment of the candidate

Response format: For each criterion, provide score/10 + detailed explanation with examples.
""",
            "pl": """
Oceń każde kryterium w skali od 1 do 10 i podaj szczegółowe wyjaśnienie z konkretnymi przykładami z rozmowy kwalifikacyjnej.

Kryteria oceny:
1. Umiejętności komunikacyjne - jasność mowy, strukturalne przedstawienie
2. Motywacja do nauki - chęć rozwoju, nauki nowych rzeczy
3. Umiejętności zawodowe - wiedza techniczna, doświadczenie w pracy
4. Myślenie analityczne - umiejętność analizy i rozwiązywania problemów
5. Myślenie nieszablonowe - kreatywność, myślenie poza schematami
6. Praca zespołowa - umiejętności współpracy w zespole
7. Odporność na stres - umiejętność pracy pod presją
8. Adaptacyjność - elastyczność, umiejętność dostosowania się do zmian
9. Kreatywność - kreatywne podejście do rozwiązywania problemów
10. Ogólne wrażenie - końcowa ocena kandydata

Format odpowiedzi: Dla każdego kryterium podaj ocenę/10 + szczegółowe wyjaśnienie z przykładami.
"""
        }
    }
    
    @staticmethod
    def get_analysis_template(template_type: str, language: str = "ru") -> str:
        """
        Получение шаблона анализа для конкретного языка
        
        Args:
            template_type: Тип шаблона
            language: Код языка
            
        Returns:
            str: Шаблон анализа
        """
        templates = PromptConfig.ANALYSIS_TEMPLATES.get(template_type, {})
        return templates.get(language, templates.get("ru", ""))