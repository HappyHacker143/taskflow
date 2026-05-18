from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver


class Department(models.Model):
    """Отдел компании"""
    name = models.CharField(max_length=200, verbose_name='Название отдела')
    description = models.TextField(blank=True, verbose_name='Описание')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Отдел'
        verbose_name_plural = 'Отделы'

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    """Профиль сотрудника компании"""
    ROLE_CHOICES = [
        ('employee', 'Сотрудник'),
        ('team_lead', 'Руководитель группы'),
        ('manager', 'Менеджер'),
        ('admin', 'Администратор'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='employees', verbose_name='Отдел')
    position = models.CharField(max_length=200, blank=True, verbose_name='Должность')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='employee', verbose_name='Роль')
    phone = models.CharField(max_length=20, blank=True, verbose_name='Телефон')
    avatar_color = models.CharField(max_length=7, default='#6366f1', verbose_name='Цвет аватара')
    # НОВОЕ: своё фото
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True,
        verbose_name='Фото профиля'
    )

    class Meta:
        verbose_name = 'Профиль сотрудника'
        verbose_name_plural = 'Профили сотрудников'

    def __str__(self):
        return f'{self.user.get_full_name()} - {self.position}'

    @property
    def display_name(self):
        if self.user.first_name and self.user.last_name:
            return f'{self.user.first_name} {self.user.last_name}'
        return self.user.username

    @property
    def initials(self):
        if self.user.first_name and self.user.last_name:
            return f'{self.user.first_name[0]}{self.user.last_name[0]}'
        return self.user.username[:2].upper()

    @property
    def avatar_url(self):
        # 1. Если загружено своё фото — используем его
        if self.avatar:
            return self.avatar.url
        # 2. Иначе — DiceBear по имени
        import urllib.parse
        first_name = self.user.first_name.strip()
        username = self.user.username
        bg = (self.avatar_color or '#6366f1').replace('#', '')
        is_female = first_name.lower().endswith(('а', 'я')) if first_name else False
        seed = urllib.parse.quote(first_name or username)
        base = f"https://api.dicebear.com/9.x/avataaars/svg?seed={seed}&backgroundColor={bg}&radius=50"
        if is_female:
            return base + "&facialHairProbability=0"
        return base

    @property
    def avatar_svg(self):
        """Fallback SVG — когда нет интернета"""
        import base64
        color = self.avatar_color or '#6366f1'
        initials = self.initials or '?'
        try:
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            text_color = '#1a1a2e' if (r * 299 + g * 587 + b * 114) / 1000 > 128 else '#ffffff'
        except Exception:
            text_color = '#ffffff'
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 40 40">'
            f'<circle cx="20" cy="20" r="20" fill="{color}"/>'
            f'<text x="20" y="20" text-anchor="middle" dominant-baseline="central" '
            f'font-family="Inter,Arial,sans-serif" font-size="14" font-weight="700" '
            f'fill="{text_color}">{initials}</text>'
            f'</svg>'
        )
        return f'data:image/svg+xml;base64,{base64.b64encode(svg.encode()).decode()}'


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Автоматически создаём профиль при создании пользователя"""
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Сохраняем профиль при сохранении пользователя"""
    if hasattr(instance, 'profile'):
        instance.profile.save()


class Project(models.Model):
    name = models.CharField(max_length=200, verbose_name='Название проекта')
    description = models.TextField(blank=True, verbose_name='Описание')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_projects')
    members = models.ManyToManyField(User, blank=True, related_name='projects')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    color = models.CharField(max_length=7, default='#4F46E5')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Проект'
        verbose_name_plural = 'Проекты'

    def __str__(self):
        return self.name

    @property
    def task_count(self):
        return self.tasks.count()

    @property
    def completed_task_count(self):
        return self.tasks.filter(status='done').count()

    @property
    def progress_percent(self):
        total = self.task_count
        if total == 0:
            return 0
        return round((self.completed_task_count / total) * 100, 1)


class Task(models.Model):
    STATUS_CHOICES = [
        ('todo', 'Не начата'),
        ('in_progress', 'В работе'),
        ('review', 'На проверке'),
        ('done', 'Завершена'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Низкий'),
        ('medium', 'Средний'),
        ('high', 'Высокий'),
        ('urgent', 'Срочный'),
    ]

    # AI-оценка сложности (без дублирования!)
    ai_complexity = models.CharField(
        max_length=20,
        choices=[('low', 'Низкая'), ('medium', 'Средняя'), ('high', 'Высокая'), ('critical', 'Критическая')],
        blank=True, null=True, verbose_name='AI: Сложность'
    )
    ai_estimated_hours = models.IntegerField(blank=True, null=True, verbose_name='AI: Оценка времени (часы)')
    ai_risk_level = models.CharField(
        max_length=20,
        choices=[('low', 'Низкий'), ('medium', 'Средний'), ('high', 'Высокий')],
        blank=True, null=True, verbose_name='AI: Уровень риска'
    )
    ai_reasoning = models.TextField(blank=True, null=True, verbose_name='AI: Обоснование оценки')
    ai_suggested_level = models.CharField(
        max_length=20,
        choices=[('junior', 'Junior'), ('middle', 'Middle'), ('senior', 'Senior')],
        blank=True, null=True, verbose_name='AI: Рекомендуемый уровень'
    )
    ai_breakdown = models.JSONField(blank=True, null=True, verbose_name='AI: Разбивка на подзадачи')

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks', verbose_name='Проект')
    title = models.CharField(max_length=300, verbose_name='Название задачи')
    description = models.TextField(blank=True, verbose_name='Описание')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='todo', verbose_name='Статус')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium', verbose_name='Приоритет')
    assignee = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='assigned_tasks', verbose_name='Исполнитель')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_tasks',
                                   verbose_name='Создатель')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    due_date = models.DateField(null=True, blank=True, verbose_name='Дата окончания')
    tags = models.CharField(max_length=500, blank=True, verbose_name='Теги (через запятую)')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Задача'
        verbose_name_plural = 'Задачи'

    def __str__(self):
        return self.title

    @property
    def is_overdue(self):
        if self.due_date and self.status != 'done':
            return self.due_date < timezone.now().date()
        return False

    @property
    def tag_list(self):
        if self.tags:
            return [t.strip() for t in self.tags.split(',') if t.strip()]
        return []

    def get_status_label(self):
        return dict(self.STATUS_CHOICES).get(self.status, self.status)

    def get_priority_label(self):
        return dict(self.PRIORITY_CHOICES).get(self.priority, self.priority)


class TaskComment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField(verbose_name='Комментарий', blank=True)
    attachment = models.FileField(
        upload_to='comment_attachments/',
        blank=True,
        null=True,
        verbose_name='Вложение'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Комментарий'
        verbose_name_plural = 'Комментарии'

    @property
    def attachment_name(self):
        if self.attachment:
            return self.attachment.name.split('/')[-1]
        return None

    @property
    def attachment_ext(self):
        if self.attachment:
            name = self.attachment.name.lower()
            if '.' in name:
                return name.split('.')[-1]
        return None

    @property
    def is_image(self):
        return self.attachment_ext in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg']

    @property
    def is_pdf(self):
        return self.attachment_ext == 'pdf'

    @property
    def is_document(self):
        return self.attachment_ext in ['doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'csv']

    def __str__(self):
        return f'Комментарий к "{self.task.title}"'