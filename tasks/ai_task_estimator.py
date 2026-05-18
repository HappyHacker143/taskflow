# tasks/ai_task_estimator.py - УМНАЯ ЭВРИСТИКА БЕЗ AI API

"""
Умная система оценки сложности задач на основе анализа ключевых слов.
БЕЗ использования внешних API - работает полностью локально!
"""

import re
from typing import Dict, List


class TaskComplexityEstimator:
    """Умная оценка сложности задач на основе эвристики"""

    def __init__(self):
        # Словари ключевых слов по сложности
        self.critical_keywords = [
            'архитектура', 'рефакторинг', 'миграция', 'масштабирование',
            'микросервис', 'kubernetes', 'docker-compose', 'ci/cd',
            'оптимизация производительности', 'безопасность критичная',
            'интеграция нескольких систем', 'распределенная система'
        ]

        self.high_keywords = [
            'интеграция', 'api', 'oauth', 'jwt', 'авторизация',
            'аутентификация', 'база данных', 'оптимизация', 'безопасность',
            'websocket', 'real-time', 'кэширование', 'redis',
            'elasticsearch', 'rabbitmq', 'celery', 'асинхронность'
        ]

        self.medium_keywords = [
            'форма', 'валидация', 'фильтр', 'поиск', 'crud',
            'страница', 'компонент', 'endpoint', 'сериализация',
            'тестирование', 'unit-тесты', 'документация',
            'рефакторинг небольшой', 'ui', 'ux'
        ]

        self.low_keywords = [
            'кнопка', 'стиль', 'css', 'цвет', 'шрифт', 'иконка',
            'текст', 'перевод', 'правка', 'исправить опечатку',
            'добавить поле', 'изменить текст'
        ]

        # Технологии и их вес сложности
        self.tech_complexity = {
            'django': 2, 'flask': 2, 'fastapi': 3,
            'react': 3, 'vue': 3, 'angular': 4,
            'postgresql': 2, 'mongodb': 3, 'redis': 2,
            'docker': 3, 'kubernetes': 5,
            'aws': 4, 'azure': 4, 'gcp': 4,
            'machine learning': 5, 'ai': 5,
            'blockchain': 5, 'websocket': 3
        }

        # Глаголы действий и их сложность
        self.action_complexity = {
            'создать': 3, 'разработать': 3, 'реализовать': 3,
            'добавить': 2, 'изменить': 2, 'обновить': 2,
            'исправить': 2, 'починить': 2, 'fix': 2,
            'оптимизировать': 4, 'рефакторить': 4,
            'интегрировать': 4, 'внедрить': 4,
            'настроить': 2, 'установить': 2,
            'спроектировать': 5, 'архитектура': 5
        }

    def estimate_task(self, title: str, description: str = "", tags: str = "") -> Dict:
        """
        Оценивает сложность задачи

        Returns:
        {
            'success': True,
            'estimation': {
                'complexity': 'low|medium|high|critical',
                'estimated_hours': int,
                'risk_level': 'low|medium|high',
                'reasoning': str,
                'suggested_assignee_level': 'junior|middle|senior',
                'breakdown': [список подзадач]
            }
        }
        """

        # Объединяем весь текст
        full_text = f"{title} {description} {tags}".lower()

        # Подсчитываем баллы
        score = 0
        matched_keywords = []

        # 1. Анализ ключевых слов по сложности
        for keyword in self.critical_keywords:
            if keyword in full_text:
                score += 10
                matched_keywords.append(('critical', keyword))

        for keyword in self.high_keywords:
            if keyword in full_text:
                score += 5
                matched_keywords.append(('high', keyword))

        for keyword in self.medium_keywords:
            if keyword in full_text:
                score += 2
                matched_keywords.append(('medium', keyword))

        for keyword in self.low_keywords:
            if keyword in full_text:
                score += 1
                matched_keywords.append(('low', keyword))

        # 2. Анализ технологий
        for tech, weight in self.tech_complexity.items():
            if tech in full_text:
                score += weight
                matched_keywords.append(('tech', tech))

        # 3. Анализ глаголов действий
        for action, weight in self.action_complexity.items():
            if action in full_text:
                score += weight

        # 4. Анализ длины текста (чем длиннее описание, тем сложнее)
        word_count = len(full_text.split())
        if word_count > 100:
            score += 5
        elif word_count > 50:
            score += 3
        elif word_count > 20:
            score += 1

        # 5. Определяем сложность
        if score >= 25:
            complexity = 'critical'
            hours = self._calculate_hours(30, 80)
            risk = 'high'
            level = 'senior'
            breakdown = self._generate_breakdown(title, description, complexity='critical')
        elif score >= 15:
            complexity = 'high'
            hours = self._calculate_hours(16, 32)
            risk = 'high' if score >= 20 else 'medium'
            level = 'senior'
            breakdown = self._generate_breakdown(title, description, complexity='high')
        elif score >= 8:
            complexity = 'medium'
            hours = self._calculate_hours(6, 16)
            risk = 'medium'
            level = 'middle'
            breakdown = []
        else:
            complexity = 'low'
            hours = self._calculate_hours(2, 6)
            risk = 'low'
            level = 'junior'
            breakdown = []

        # 6. Генерируем обоснование
        reasoning = self._generate_reasoning(
            complexity, matched_keywords, word_count, title
        )

        return {
            'success': True,
            'estimation': {
                'complexity': complexity,
                'estimated_hours': hours,
                'risk_level': risk,
                'reasoning': reasoning,
                'suggested_assignee_level': level,
                'breakdown': breakdown
            }
        }

    def _calculate_hours(self, min_hours: int, max_hours: int) -> int:
        """Рассчитывает среднее время"""
        return (min_hours + max_hours) // 2

    def _generate_reasoning(self, complexity: str, keywords: List, word_count: int, title: str) -> str:
        """Генерирует обоснование оценки"""

        if complexity == 'critical':
            base = "Задача критически сложная. "
            if any(k[1] in ['архитектура', 'микросервис', 'kubernetes'] for k in keywords):
                base += "Требуется проектирование архитектуры и работа с инфраструктурой. "
            base += "Необходима декомпозиция на подзадачи. Высокие риски и много зависимостей."

        elif complexity == 'high':
            base = "Задача высокой сложности. "
            tech_keywords = [k[1] for k in keywords if k[0] in ['high', 'tech']]
            if tech_keywords:
                base += f"Требуется работа с технологиями: {', '.join(tech_keywords[:3])}. "
            base += "Нужен опытный разработчик. Средние или высокие риски."

        elif complexity == 'medium':
            base = "Задача средней сложности. "
            if 'интеграция' in title.lower() or 'api' in title.lower():
                base += "Требуется интеграция с внешними системами. "
            else:
                base += "Стандартная разработка функционала. "
            base += "Подходит для разработчика уровня Middle."

        else:  # low
            base = "Простая задача. "
            if any(k[1] in ['кнопка', 'стиль', 'css', 'текст'] for k in keywords):
                base += "Косметические изменения или простые правки. "
            else:
                base += "Небольшой объём работы с понятными требованиями. "
            base += "Подходит для начинающего разработчика."

        # Добавляем инфо о длине описания
        if word_count > 50:
            base += f" Подробное описание ({word_count} слов) указывает на множество деталей."

        return base

    def _generate_breakdown(self, title: str, description: str, complexity: str) -> List[str]:
        """Генерирует разбивку на подзадачи для сложных задач"""

        if complexity not in ['high', 'critical']:
            return []

        breakdown = []
        text = f"{title} {description}".lower()

        # Универсальные подзадачи
        if complexity == 'critical':
            breakdown.append("Анализ требований и проектирование архитектуры")

        # Специфичные подзадачи на основе ключевых слов
        if 'api' in text or 'интеграция' in text:
            breakdown.append("Проектирование API endpoints")
            breakdown.append("Реализация интеграции")
            breakdown.append("Обработка ошибок и edge cases")

        if 'база данных' in text or 'postgresql' in text or 'mongodb' in text:
            breakdown.append("Проектирование схемы базы данных")
            breakdown.append("Написание миграций")

        if 'ui' in text or 'интерфейс' in text or 'страница' in text:
            breakdown.append("Разработка UI компонентов")
            breakdown.append("Адаптивная вёрстка")

        if 'авторизация' in text or 'аутентификация' in text or 'oauth' in text:
            breakdown.append("Настройка системы аутентификации")
            breakdown.append("Реализация защиты endpoints")

        # Всегда добавляем тестирование для сложных задач
        breakdown.append("Написание unit-тестов")

        if complexity == 'critical':
            breakdown.append("Интеграционное тестирование")
            breakdown.append("Документирование решения")

        # Финальная проверка
        if breakdown:
            breakdown.append("Code review и рефакторинг")

        return breakdown[:6]  # Максимум 6 подзадач


# Для обратной совместимости
def estimate_task_complexity(title: str, description: str = "", tags: str = "") -> Dict:
    """Вспомогательная функция для прямого вызова"""
    estimator = TaskComplexityEstimator()
    return estimator.estimate_task(title, description, tags)