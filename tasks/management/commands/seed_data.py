from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from tasks.models import Project, Task, TaskComment, Department, UserProfile
from django.utils import timezone
import random


class Command(BaseCommand):
    help = 'Seed demo data for TaskFlow'

    def handle(self, *args, **options):
        self.stdout.write('Seeding demo data...')

        # ─── Departments ────
        dept_data = [
            ('Разработка', 'Команда разработчиков программного обеспечения'),
            ('Дизайн', 'Команда UI/UX дизайнеров'),
            ('Менеджмент', 'Руководство и управление проектами'),
            ('Маркетинг', 'Отдел маркетинга и продвижения'),
        ]
        departments = {}
        for name, desc in dept_data:
            dept, created = Department.objects.get_or_create(
                name=name,
                defaults={'description': desc}
            )
            departments[name] = dept
            if created:
                self.stdout.write(f'  Created department: {name}')

        # ─── Users ────
        users = []
        user_data = [
            ('admin', 'admin', 'Иван', 'Петров', 'ivan@company.com', departments['Менеджмент'], 'Руководитель проектов', 'admin', '+7 (999) 111-11-11', '#6366f1'),
            ('maria', 'maria123', 'Мария', 'Сидорова', 'maria@company.com', departments['Разработка'], 'Frontend разработчик', 'employee', '+7 (999) 222-22-22', '#ec4899'),
            ('alex', 'alex123', 'Алексей', 'Козлов', 'alex@company.com', departments['Разработка'], 'Backend разработчик', 'team_lead', '+7 (999) 333-33-33', '#10b981'),
            ('julia', 'julia123', 'Юлия', 'Новикова', 'julia@company.com', departments['Дизайн'], 'UI/UX дизайнер', 'employee', '+7 (999) 444-44-44', '#f59e0b'),
        ]
        for username, password, first, last, email, dept, position, role, phone, color in user_data:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'first_name': first, 'last_name': last, 'email': email}
            )
            if created:
                user.set_password(password)
                user.save()
                self.stdout.write(f'  Created user: {username} / {password}')
            
            # Update profile
            profile = user.profile
            profile.department = dept
            profile.position = position
            profile.role = role
            profile.phone = phone
            profile.avatar_color = color
            profile.save()
            
            users.append(user)

        admin_user = users[0]

        # ─── Projects ─
        project_data = [
            ('Сайт компании', 'Разработка корпоративного сайта с CMS и личным кабинетом', '#4F46E5'),
            ('Мобильное приложение', 'iOS и Android приложение для клиентов банка', '#10B981'),
            ('API Backend', 'Microservices архитектура для основной платформы', '#F59E0B'),
            ('Ребрендинг', 'Обновление брендайнга компании и маркетинговых материалов', '#EF4444'),
        ]
        projects = []
        for name, desc, color in project_data:
            project, created = Project.objects.get_or_create(
                name=name,
                defaults={
                    'description': desc,
                    'color': color,
                    'created_by': admin_user,
                }
            )
            if created:
                project.members.set(users[1:])
            projects.append(project)

        # ─── Tasks ────
        task_templates = [
            # Project 0 — Сайт компании
            ('Проработать макеты главной страницы', 'Согласовать дизайн с заказчиком', 'done', 'high', users[1], projects[0], ['дизайн', 'UI']),
            ('Реализация CMS на Django', 'Модули статей, новостей, контактов', 'in_progress', 'urgent', users[2], projects[0], ['backend', 'django']),
            ('Адаптация сайта под мобиль', 'Media queries и тестирование', 'todo', 'medium', users[1], projects[0], ['frontend', 'css']),
            ('Интеграция с аналитикой', 'Подключить Google Analytics и Yandex Metrika', 'review', 'low', users[3], projects[0], ['аналитика']),
            ('SEO оптимизация', 'Meta tags, sitemap, schema.org', 'todo', 'medium', users[2], projects[0], ['seo']),

            # Project 1 — Мобильное приложение
            ('Авторизация и регистрация', 'OAuth2 + SMS OTP', 'done', 'urgent', users[2], projects[1], ['auth', 'mobile']),
            ('Экран профиля пользователя', 'Редактирование данных, фото', 'in_progress', 'high', users[3], projects[1], ['ui', 'mobile']),
            ('Push-уведомления', 'FCM интеграция', 'todo', 'medium', users[1], projects[1], ['backend']),
            ('Тестирование на iOS', 'TestFlight дистрибуция', 'todo', 'high', users[2], projects[1], ['testing', 'ios']),

            # Project 2 — API Backend
            ('Микросервис аутентификации', 'JWT + refresh tokens', 'done', 'urgent', users[2], projects[2], ['api', 'security']),
            ('Микросервис уведомлений', 'Email + SMS + Push', 'in_progress', 'high', users[3], projects[2], ['api', 'notifications']),
            ('Документация API', 'Swagger / OpenAPI spec', 'review', 'medium', users[1], projects[2], ['docs', 'api']),
            ('Load testing', 'Locust или k6 нагрузочные тесты', 'todo', 'high', users[2], projects[2], ['testing']),

            # Project 3 — Ребрендинг
            ('Новый логотип компании', 'Finalize with designer', 'done', 'high', users[3], projects[3], ['дизайн', 'бренд']),
            ('Обновить визуальные гайдлайны', 'Цвета, шрифты, компоненты', 'in_progress', 'medium', users[1], projects[3], ['дизайн']),
            ('Обновить соцсети', 'Аватары, баннеры, шаблоны', 'todo', 'low', users[3], projects[3], ['маркетинг']),
        ]

        for title, desc, status, priority, assignee, project, tags in task_templates:
            task, created = Task.objects.get_or_create(
                title=title,
                project=project,
                defaults={
                    'description': desc,
                    'status': status,
                    'priority': priority,
                    'assignee': assignee,
                    'created_by': admin_user,
                    'tags': ', '.join(tags),
                    'due_date': timezone.now().date() + timezone.timedelta(days=random.randint(-5, 30)),
                }
            )
            if created and status == 'done':
                task.due_date = timezone.now().date() - timezone.timedelta(days=random.randint(1, 10))
                task.save()

        # ─── Comments ─
        comments = [
            (projects[0].tasks.first(), users[1], 'Макеты согласованы, можно начинать вёрстку.'),
            (projects[0].tasks.first(), users[0], 'Отлично! Поставим в приоритет.'),
            (projects[1].tasks.filter(status='in_progress').first(), users[2], 'Нужно уточнить требования по фото.'),
            (projects[2].tasks.filter(status='in_progress').first(), users[0], 'Добавьте логирование ошибок.'),
        ]
        for task, author, text in comments:
            if task:
                TaskComment.objects.get_or_create(
                    task=task,
                    author=author,
                    text=text,
                )

        self.stdout.write(self.style.SUCCESS('Demo data seeded successfully!'))
        self.stdout.write('─' * 40)
        self.stdout.write('Login credentials:')
        self.stdout.write('  admin  / admin  (Администратор)')
        self.stdout.write('  maria  / maria123  (Frontend разработчик)')
        self.stdout.write('  alex   / alex123  (Backend Team Lead)')
        self.stdout.write('  julia  / julia123  (UI/UX дизайнер)')
