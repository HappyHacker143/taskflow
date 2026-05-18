from datetime import datetime, timedelta
import calendar
import csv
import json

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .ai_task_estimator import TaskComplexityEstimator
from .forms import CommentForm, ProjectForm, TaskForm, UserCreateForm, UserEditForm
from .models import Department, Project, Task, TaskActivity
from .permissions import (
    can_edit_project,
    can_edit_task,
    editable_projects,
    is_admin,
    visible_projects,
    visible_tasks,
)

# ─── HELPERS ─────────────────────────────────────────────

def get_visible_project_or_404(user, pk):
    return get_object_or_404(visible_projects(user), pk=pk)


def get_editable_project_or_404(user, pk):
    project = get_object_or_404(editable_projects(user), pk=pk)
    if not can_edit_project(user, project):
        raise PermissionDenied
    return project


def get_visible_task_or_404(user, pk):
    return get_object_or_404(visible_tasks(user).select_related('project', 'assignee', 'created_by'), pk=pk)


def get_editable_task_or_404(user, pk):
    task = get_object_or_404(visible_tasks(user).select_related('project', 'assignee', 'created_by'), pk=pk)
    if not can_edit_task(user, task):
        raise PermissionDenied
    return task


def log_task_activity(task, actor, action, description='', metadata=None):
    TaskActivity.objects.create(
        task=task,
        actor=actor if actor.is_authenticated else None,
        action=action,
        description=description,
        metadata=metadata or {},
    )


@login_required
@require_POST
def estimate_task_complexity(request):
    """AJAX endpoint для оценки сложности задачи"""
    try:
        data = json.loads(request.body or '{}')
        title = data.get('title', '')
        description = data.get('description', '')
        tags = data.get('tags', '')

        if not title:
            return JsonResponse({'error': 'Название задачи обязательно'}, status=400)

        estimator = TaskComplexityEstimator()
        result = estimator.estimate_task(title, description, tags)

        if result['success']:
            return JsonResponse({
                'success': True,
                'estimation': result['estimation']
            })
        return JsonResponse({'error': 'Ошибка оценки'}, status=500)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Некорректный JSON'}, status=400)
    except Exception:
        return JsonResponse({'error': 'Не удалось оценить задачу'}, status=500)


# ─── AUTH ────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('dashboard')
        messages.error(request, 'Неверный логин или пароль.')
    return render(request, 'tasks/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


# ─── DASHBOARD ───────────────────────────────────────────

@login_required
def dashboard(request):
    # Проекты пользователя
    user_projects = visible_projects(request.user)

    # Задачи пользователя
    user_tasks = visible_tasks(request.user).filter(assignee=request.user).select_related('project')

    # Базовая статистика
    total_tasks = user_tasks.count()
    completed_tasks = user_tasks.filter(status='done').count()
    pending_tasks = user_tasks.exclude(status='done').count()
    overdue_tasks = user_tasks.filter(
        due_date__lt=timezone.now().date(),
        status__in=['todo', 'in_progress', 'review']
    ).count()

    # Статистика по статусам для графика
    tasks_by_status = {
        'todo': user_tasks.filter(status='todo').count(),
        'in_progress': user_tasks.filter(status='in_progress').count(),
        'review': user_tasks.filter(status='review').count(),
        'done': user_tasks.filter(status='done').count(),
    }

    # Статистика по приоритетам
    tasks_by_priority = {
        'low': user_tasks.filter(priority='low').count(),
        'medium': user_tasks.filter(priority='medium').count(),
        'high': user_tasks.filter(priority='high').count(),
        'urgent': user_tasks.filter(priority='urgent').count(),
    }

    # Задачи за последние 7 дней (для графика активности)
    last_7_days = []
    tasks_last_7_days = []
    for i in range(6, -1, -1):
        day = timezone.now().date() - timedelta(days=i)
        last_7_days.append(day.strftime('%d.%m'))
        count = user_tasks.filter(created_at__date=day).count()
        tasks_last_7_days.append(count)

    # Ближайшие дедлайны (для AI ассистента)
    upcoming_deadlines = user_tasks.filter(
        due_date__gte=timezone.now().date(),
        status__in=['todo', 'in_progress', 'review']
    ).order_by('due_date')[:3]

    # НОВОЕ: Задачи которые скоро просрочатся (через 1-2 дня)
    today = timezone.now().date()
    soon_deadline = today + timedelta(days=2)  # Через 2 дня

    soon_overdue_tasks = user_tasks.filter(
        due_date__gt=today,
        due_date__lte=soon_deadline,
        status__in=['todo', 'in_progress', 'review']
    ).order_by('due_date')

    # Добавляем количество дней до дедлайна для каждой задачи
    for task in soon_overdue_tasks:
        task.days_until_due = (task.due_date - today).days

    # Последние активности
    recent_tasks = user_tasks.order_by('-created_at')[:5]

    # Нагрузка команды (для admin/managers)
    team_workload = None
    if request.user.is_superuser or request.user.profile.role in ['admin', 'manager']:
        from django.contrib.auth.models import User
        team_workload = User.objects.filter(
            assigned_tasks__is_archived=False
        ).annotate(
            active_tasks=Count('assigned_tasks', filter=Q(assigned_tasks__status__in=['todo', 'in_progress', 'review'], assigned_tasks__is_archived=False))
        ).order_by('-active_tasks')[:5]

    context = {
        'user_projects': user_projects[:5],
        'recent_tasks': recent_tasks,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'pending_tasks': pending_tasks,
        'overdue_tasks': overdue_tasks,
        'tasks_by_status': tasks_by_status,
        'tasks_by_priority': tasks_by_priority,
        'last_7_days': last_7_days,
        'tasks_last_7_days': tasks_last_7_days,
        'upcoming_deadlines': upcoming_deadlines,
        'soon_overdue_tasks': soon_overdue_tasks,  # НОВОЕ
        'soon_overdue_count': soon_overdue_tasks.count(),  # НОВОЕ - для бейджа
        'team_workload': team_workload,
    }

    return render(request, 'tasks/dashboard.html', context)


# ─── PROJECTS ────────────────────────────────────────────

@login_required
def project_list(request):
    projects = list(visible_projects(request.user).annotate(
        annotated_task_count=Count('tasks', filter=Q(tasks__is_archived=False), distinct=True),
        annotated_completed_task_count=Count(
            'tasks',
            filter=Q(tasks__status='done', tasks__is_archived=False),
            distinct=True,
        ),
    ).prefetch_related('members', 'members__profile'))
    for project in projects:
        project.can_edit_current_project = can_edit_project(request.user, project)
    return render(request, 'tasks/project_list.html', {'projects': projects})

@login_required
def project_create(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.created_by = request.user
            project.save()
            form.save_m2m()
            project.members.add(request.user)
            messages.success(request, f'Проект "{project.name}" создан.')
            return redirect('project_detail', pk=project.pk)
    else:
        form = ProjectForm()
    return render(request, 'tasks/project_form.html', {'form': form, 'title': 'Новый проект'})


@login_required
def project_detail(request, pk):
    project = get_visible_project_or_404(request.user, pk)
    tasks = visible_tasks(request.user).filter(project=project).select_related('assignee', 'created_by')

    status_filter = request.GET.get('status')
    if status_filter:
        tasks = tasks.filter(status=status_filter)

    search = request.GET.get('search', '').strip()
    if search:
        tasks = tasks.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search) |
            Q(tags__icontains=search)
        )

    kanban = {
        'todo': tasks.filter(status='todo'),
        'in_progress': tasks.filter(status='in_progress'),
        'review': tasks.filter(status='review'),
        'done': tasks.filter(status='done'),
    }

    kanban_columns = [
        ('todo', 'Не начата'),
        ('in_progress', 'В работе'),
        ('review', 'На проверке'),
        ('done', 'Завершена'),
    ]

    context = {
        'project': project,
        'can_edit_current_project': can_edit_project(request.user, project),
        'tasks': tasks,
        'kanban_dict': kanban,
        'kanban_columns': kanban_columns,
        'status_filter': status_filter,
        'search': search,
    }
    return render(request, 'tasks/project_detail.html', context)


@login_required
def project_export_csv(request, pk):
    project = get_visible_project_or_404(request.user, pk)
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="project-{project.pk}-tasks.csv"'
    response.write('﻿')
    writer = csv.writer(response)
    writer.writerow(['Проект', project.name])
    writer.writerow([])
    writer.writerow(['Задача', 'Статус', 'Приоритет', 'Исполнитель', 'Дедлайн', 'Создана'])
    for task in visible_tasks(request.user).filter(project=project).select_related('assignee').order_by('due_date', 'title'):
        writer.writerow([
            task.title,
            task.get_status_display(),
            task.get_priority_display(),
            task.assignee.profile.display_name if task.assignee else 'Не назначено',
            task.due_date.strftime('%d.%m.%Y') if task.due_date else '',
            task.created_at.strftime('%d.%m.%Y %H:%M'),
        ])
    return response

@login_required
def project_edit(request, pk):
    project = get_editable_project_or_404(request.user, pk)
    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, 'Проект обновлён.')
            return redirect('project_detail', pk=project.pk)
    else:
        form = ProjectForm(instance=project)
        form.initial['members'] = list(project.members.values_list('id', flat=True))
    return render(request, 'tasks/project_form.html', {'form': form, 'title': 'Редактировать проект'})

@login_required
def project_delete(request, pk):
    project = get_editable_project_or_404(request.user, pk)
    if request.method == 'POST':
        project.is_archived = True
        project.tasks.update(is_archived=True)
        project.save(update_fields=['is_archived', 'updated_at'])
        messages.success(request, 'Проект перемещён в архив.')
        return redirect('project_list')
    return render(request, 'tasks/project_delete.html', {'project': project})

# ─── TASKS ───────────────────────────────────────────────

@login_required
def task_create(request, project_pk=None):
    initial = {}
    if project_pk:
        project = get_editable_project_or_404(request.user, project_pk)
        initial['project'] = project.pk

    if request.method == 'POST':
        form = TaskForm(request.POST, user=request.user)
        if form.is_valid():
            task = form.save(commit=False)
            task.created_by = request.user
            task.save()
            log_task_activity(task, request.user, TaskActivity.ACTION_TASK_CREATED, 'Задача создана')
            messages.success(request, f'Задача "{task.title}" создана.')
            return redirect('project_detail', pk=task.project.pk)
    else:
        form = TaskForm(user=request.user, initial=initial)
    return render(request, 'tasks/task_form.html', {'form': form, 'title': 'Новая задача'})

@login_required
def task_detail(request, pk):
    task = get_visible_task_or_404(request.user, pk)
    comments = task.comments.all().select_related('author', 'author__profile').order_by('created_at')
    activities = task.activities.select_related('actor', 'actor__profile')[:20]

    if request.method == 'POST':
        form = CommentForm(request.POST, request.FILES)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.task = task
            comment.author = request.user
            comment.save()
            log_task_activity(task, request.user, TaskActivity.ACTION_COMMENT_ADDED, 'Комментарий добавлен')
            messages.success(request, 'Комментарий добавлен!')
            return redirect('task_detail', pk=task.pk)
    else:
        form = CommentForm()

    context = {
        'task': task,
        'comments': comments,
        'activities': activities,
        'form': form,
        'can_edit_current_task': can_edit_task(request.user, task),
    }
    return render(request, 'tasks/task_detail.html', context)

@login_required
def task_edit(request, pk):
    task = get_editable_task_or_404(request.user, pk)
    old_status = task.status
    old_assignee_id = task.assignee_id
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task, user=request.user)
        if form.is_valid():
            task = form.save()
            log_task_activity(task, request.user, TaskActivity.ACTION_TASK_UPDATED, 'Задача обновлена')
            if old_status != task.status:
                log_task_activity(
                    task,
                    request.user,
                    TaskActivity.ACTION_STATUS_CHANGED,
                    f'Статус изменён: {old_status} → {task.status}',
                    {'from': old_status, 'to': task.status},
                )
            if old_assignee_id != task.assignee_id:
                log_task_activity(
                    task,
                    request.user,
                    TaskActivity.ACTION_ASSIGNEE_CHANGED,
                    'Исполнитель изменён',
                    {'from': old_assignee_id, 'to': task.assignee_id},
                )
            messages.success(request, 'Задача обновлена.')
            return redirect('task_detail', pk=task.pk)
    else:
        form = TaskForm(instance=task, user=request.user)
    return render(request, 'tasks/task_form.html', {'form': form, 'title': 'Редактировать задачу'})

@login_required
def task_delete(request, pk):
    task = get_editable_task_or_404(request.user, pk)
    project_pk = task.project.pk
    if request.method == 'POST':
        task.is_archived = True
        task.save(update_fields=['is_archived', 'updated_at'])
        log_task_activity(task, request.user, TaskActivity.ACTION_TASK_ARCHIVED, 'Задача перемещена в архив')
        messages.success(request, 'Задача перемещена в архив.')
        return redirect('project_detail', pk=project_pk)
    return render(request, 'tasks/task_delete.html', {'task': task})

# ─── COMMENTS ────────────────────────────────────────────

@login_required
@require_POST
def add_comment(request, task_pk):
    task = get_visible_task_or_404(request.user, task_pk)
    form = CommentForm(request.POST, request.FILES)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.task = task
        comment.author = request.user
        comment.save()
        log_task_activity(task, request.user, TaskActivity.ACTION_COMMENT_ADDED, 'Комментарий добавлен')
        messages.success(request, 'Комментарий добавлен.')
    else:
        messages.error(request, 'Комментарий не сохранён. Проверьте текст или вложение.')
    return redirect('task_detail', pk=task.pk)


# ─── AJAX: Update task status ────────────────────────────

@login_required
@require_POST
def task_update_status(request, pk):
    task = get_editable_task_or_404(request.user, pk)
    old_status = task.status
    new_status = request.POST.get('status')
    if new_status in dict(Task.STATUS_CHOICES):
        task.status = new_status
        task.save(update_fields=['status', 'updated_at'])
        if old_status != new_status:
            log_task_activity(
                task,
                request.user,
                TaskActivity.ACTION_STATUS_CHANGED,
                f'Статус изменён: {old_status} → {new_status}',
                {'from': old_status, 'to': new_status},
            )
        return JsonResponse({'success': True, 'status': new_status, 'status_display': task.get_status_display()})
    return JsonResponse({'success': False, 'error': 'Некорректный статус'}, status=400)


# ─── ALL TASKS (my tasks view) ───────────────────────────

@login_required
def my_tasks(request):
    tasks = visible_tasks(request.user).filter(assignee=request.user).select_related('project')
    status_filter = request.GET.get('status')
    if status_filter:
        tasks = tasks.filter(status=status_filter)
    search = request.GET.get('search', '').strip()
    if search:
        tasks = tasks.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search)
        )
    return render(request, 'tasks/my_tasks.html', {'tasks': tasks, 'status_filter': status_filter, 'search': search})

# ─── USER MANAGEMENT (ADMIN ONLY) ───────────────────────

@login_required
@user_passes_test(is_admin)
def user_list(request):
    """Список всех пользователей (только для админов)"""
    users = User.objects.select_related('profile', 'profile__department').order_by('first_name', 'last_name')
    departments = Department.objects.all()

    # Фильтр по отделу
    dept_filter = request.GET.get('department')
    if dept_filter:
        users = users.filter(profile__department_id=dept_filter)

    # Поиск
    search = request.GET.get('search', '').strip()
    if search:
        users = users.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(profile__position__icontains=search)
        )

    context = {
        'users': users,
        'departments': departments,
        'dept_filter': dept_filter,
        'search': search,
    }
    return render(request, 'tasks/user_list.html', context)


@login_required
@user_passes_test(is_admin)
def user_create(request):
    """Создание нового пользователя (только админ)"""
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'Пользователь "{user.get_full_name()}" успешно создан.')
            return redirect('user_list')
    else:
        form = UserCreateForm()
    return render(request, 'tasks/user_form.html', {'form': form, 'title': 'Новый сотрудник'})


@login_required
@user_passes_test(is_admin)
def user_edit(request, pk):
    """Редактирование пользователя (только админ)"""
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        # ВАЖНО: передаём request.FILES для загрузки аватара
        form = UserEditForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, f'Данные пользователя "{user.get_full_name()}" обновлены.')
            return redirect('user_list')
    else:
        form = UserEditForm(instance=user)
    return render(request, 'tasks/user_form.html', {
        'form': form,
        'title': f'Редактировать: {user.get_full_name()}'
    })


@login_required
@user_passes_test(is_admin)
def user_delete(request, pk):
    """Удаление/деактивация пользователя (только админ)"""
    user = get_object_or_404(User, pk=pk)
    if request.user == user:
        messages.error(request, 'Вы не можете удалить свой собственный аккаунт.')
        return redirect('user_list')

    if request.method == 'POST':
        user.is_active = False
        user.save()
        messages.success(request, f'Пользователь "{user.get_full_name()}" деактивирован.')
        return redirect('user_list')
    return render(request, 'tasks/user_delete.html', {'user_obj': user})


@login_required
@user_passes_test(is_admin)
def department_list(request):
    """Список отделов (только админ)"""
    departments = Department.objects.annotate(
        employee_count=Count('employees')
    ).order_by('name')
    return render(request, 'tasks/department_list.html', {'departments': departments})


@login_required
def calendar_view(request):
    year = int(request.GET.get('year', timezone.now().year))
    month = int(request.GET.get('month', timezone.now().month))

    cal = calendar.monthcalendar(year, month)
    month_name = calendar.month_name[month]

    user_tasks = visible_tasks(request.user).filter(
        assignee=request.user,
        due_date__isnull=False,
    ).select_related('project')

    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    context = {
        'calendar': cal,
        'year': year,
        'month': month,
        'month_name': month_name,
        'user_tasks': user_tasks,
        'prev_month': prev_month,
        'prev_year': prev_year,
        'next_month': next_month,
        'next_year': next_year,
        'today': timezone.now().date(),
    }

    return render(request, 'tasks/calendar.html', context)


@login_required
def kanban_view(request):
    """Kanban доска с фильтрами"""
    selected_project = request.GET.get('project', '')
    selected_assignee = request.GET.get('assignee', '')
    selected_priority = request.GET.get('priority', '')
    search_query = request.GET.get('search', '').strip()

    filtered_tasks = visible_tasks(request.user).select_related('project', 'assignee', 'assignee__profile')

    if selected_project:
        filtered_tasks = filtered_tasks.filter(project_id=selected_project)
    if selected_assignee:
        filtered_tasks = filtered_tasks.filter(assignee_id=selected_assignee)
    if selected_priority:
        filtered_tasks = filtered_tasks.filter(priority=selected_priority)
    if search_query:
        filtered_tasks = filtered_tasks.filter(title__icontains=search_query)

    tasks_by_status = {
        'todo': filtered_tasks.filter(status='todo').order_by('-priority', 'due_date'),
        'in_progress': filtered_tasks.filter(status='in_progress').order_by('-priority', 'due_date'),
        'review': filtered_tasks.filter(status='review').order_by('-priority', 'due_date'),
        'done': filtered_tasks.filter(status='done').order_by('-updated_at')[:20],
    }

    available_projects = visible_projects(request.user).distinct()
    available_assignees = User.objects.filter(
        Q(projects__in=available_projects) | Q(assigned_tasks__project__in=available_projects),
        is_active=True,
    ).select_related('profile').distinct().order_by('first_name', 'last_name')

    context = {
        'tasks_by_status': tasks_by_status,
        'total_tasks': filtered_tasks.count(),
        'available_projects': available_projects,
        'available_assignees': available_assignees,
        'selected_project': selected_project,
        'selected_assignee': selected_assignee,
        'selected_priority': selected_priority,
        'search_query': search_query,
        'priorities': [
            ('low', 'Низкий'),
            ('medium', 'Средний'),
            ('high', 'Высокий'),
            ('urgent', 'Срочный'),
        ],
    }

    return render(request, 'tasks/kanban.html', context)


@login_required
@require_POST
def kanban_update_status(request):
    """AJAX endpoint для обновления статуса задачи из JSON-запроса"""
    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Некорректный JSON'}, status=400)

    task_id = data.get('task_id')
    new_status = data.get('status')
    if new_status not in dict(Task.STATUS_CHOICES):
        return JsonResponse({'success': False, 'error': 'Некорректный статус'}, status=400)

    task = get_editable_task_or_404(request.user, task_id)
    old_status = task.status
    task.status = new_status
    task.save(update_fields=['status', 'updated_at'])
    if old_status != new_status:
        log_task_activity(
            task,
            request.user,
            TaskActivity.ACTION_STATUS_CHANGED,
            f'Статус изменён: {old_status} → {new_status}',
            {'from': old_status, 'to': new_status},
        )

    return JsonResponse({
        'success': True,
        'task_id': task.id,
        'new_status': new_status,
        'status_display': task.get_status_display(),
    })


@login_required
def live_tasks(request):
    """Лёгкий polling endpoint для синхронизации статусов задач на открытых досках."""
    updated_after = request.GET.get('updated_after')
    tasks = visible_tasks(request.user).select_related('project')
    if updated_after:
        try:
            parsed = datetime.fromisoformat(updated_after.replace('Z', '+00:00'))
            tasks = tasks.filter(updated_at__gt=parsed)
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Некорректная дата'}, status=400)

    payload = [
        {
            'id': task.id,
            'status': task.status,
            'status_display': task.get_status_display(),
            'project_id': task.project_id,
            'updated_at': task.updated_at.isoformat(),
        }
        for task in tasks.order_by('-updated_at')[:100]
    ]
    return JsonResponse({'success': True, 'tasks': payload, 'server_time': timezone.now().isoformat()})
