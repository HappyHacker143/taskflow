# quick_export.py - Быстрый экспорт БД

"""
ИСПОЛЬЗОВАНИЕ:
python manage.py shell < quick_export.py > database_dump.txt
"""

from django.contrib.auth.models import User
from tasks.models import *
from django.utils import timezone

print("="*80)
print("БАЗА ДАННЫХ TASKFLOW - ЭКСПОРТ")
print(f"Дата: {timezone.now()}")
print("="*80)

# ПОЛЬЗОВАТЕЛИ
print("\n\n### ПОЛЬЗОВАТЕЛИ ###\n")
for user in User.objects.all():
    print(f"\nID: {user.id} | {user.username} | {user.email}")
    print(f"Имя: {user.first_name} {user.last_name}")
    if hasattr(user, 'profile'):
        print(f"Роль: {user.profile.get_role_display()}")
        print(f"Должность: {user.profile.position}")

# ОТДЕЛЫ
print("\n\n### ОТДЕЛЫ ###\n")
for dept in Department.objects.all():
    print(f"\nID: {dept.id} | {dept.name}")
    print(f"Описание: {dept.description}")

# ПРОЕКТЫ
print("\n\n### ПРОЕКТЫ ###\n")
for project in Project.objects.all():
    print(f"\nID: {project.id} | {project.name}")
    print(f"Описание: {project.description}")
    print(f"Создатель: {project.created_by.username}")
    print(f"Участники: {', '.join([m.username for m in project.members.all()])}")

# ЗАДАЧИ
print("\n\n### ЗАДАЧИ ###\n")
for task in Task.objects.all():
    print(f"\nID: {task.id} | {task.title}")
    print(f"Проект: {task.project.name}")
    print(f"Статус: {task.get_status_display()}")
    print(f"Приоритет: {task.get_priority_display()}")
    print(f"Исполнитель: {task.assignee.username if task.assignee else 'Не назначен'}")
    print(f"Описание: {task.description}")
    print(f"Дедлайн: {task.due_date}")

# КОММЕНТАРИИ
print("\n\n### КОММЕНТАРИИ ###\n")
for comment in TaskComment.objects.all():
    print(f"\nID: {comment.id}")
    print(f"Задача: {comment.task.title}")
    print(f"Автор: {comment.author.username}")
    print(f"Текст: {comment.text}")
    print(f"Дата: {comment.created_at}")

# СТАТИСТИКА
print("\n\n### СТАТИСТИКА ###\n")
print(f"Всего пользователей: {User.objects.count()}")
print(f"Всего проектов: {Project.objects.count()}")
print(f"Всего задач: {Task.objects.count()}")
print(f"Всего комментариев: {TaskComment.objects.count()}")
print(f"\nЗадачи по статусам:")
print(f"  К выполнению: {Task.objects.filter(status='todo').count()}")
print(f"  В работе: {Task.objects.filter(status='in_progress').count()}")
print(f"  На проверке: {Task.objects.filter(status='review').count()}")
print(f"  Выполнено: {Task.objects.filter(status='done').count()}")

print("\n" + "="*80)
print("ЭКСПОРТ ЗАВЕРШЁН")
print("="*80)
