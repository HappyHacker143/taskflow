from datetime import datetime, timedelta
from django.utils import timezone
import calendar
from django.db.models import Count, Q
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Q, Count
from django.contrib.auth.models import User
from .models import Project, Task, TaskComment, Department, UserProfile
from .forms import ProjectForm, TaskForm, CommentForm, UserCreateForm, UserEditForm
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json

# ─── HELPERS ─────────────────────────────────────────────

def is_admin(user):
    """Проверка, является ли пользователь администратором"""
    return user.is_authenticated and (user.is_superuser or user.profile.role == 'admin')


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
    user_projects = Project.objects.filter(members=request.user)

    # Задачи пользователя
    user_tasks = Task.objects.filter(assignee=request.user).select_related('project')

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
            assigned_tasks__isnull=False
        ).annotate(
            active_tasks=Count('assigned_tasks', filter=Q(assigned_tasks__status__in=['todo', 'in_progress', 'review']))
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
    projects = Project.objects.filter(
        Q(created_by=request.user) | Q(members=request.user)
    ).distinct()
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
            messages.success(request, f'Проект "{project.name}" создан.')
            return redirect('project_detail', pk=project.pk)
    else:
        form = ProjectForm()
    return render(request, 'tasks/project_form.html', {'form': form, 'title': 'Новый проект'})


@login_required
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    tasks = project.tasks.all()

    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        tasks = tasks.filter(status=status_filter)

    # Search
    search = request.GET.get('search', '').strip()
    if search:
        tasks = tasks.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search) |
            Q(tags__icontains=search)
        )

    # Group tasks by status for Kanban
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
        'tasks': tasks,
        'kanban_dict': kanban,
        'kanban_columns': kanban_columns,
        'status_filter': status_filter,
        'search': search,
    }
    return render(request, 'tasks/project_detail.html', context)


@login_required
def project_edit(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, 'Проект обновлён.')
            return redirect('project_detail', pk=project.pk)
    else:
        form = ProjectForm(instance=project)
        # Передаём initial members для правильного отображения
        form.initial['members'] = list(project.members.values_list('id', flat=True))
    return render(request, 'tasks/project_form.html', {'form': form, 'title': 'Редактировать проект'})


@login_required
def project_delete(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.method == 'POST':
        project.delete()
        messages.success(request, 'Проект удалён.')
        return redirect('project_list')
    return render(request, 'tasks/project_delete.html', {'project': project})


# ─── TASKS ───────────────────────────────────────────────

@login_required
def task_create(request, project_pk=None):
    if request.method == 'POST':
        form = TaskForm(request.POST, user=request.user)
        if form.is_valid():
            task = form.save(commit=False)
            task.created_by = request.user
            task.save()
            messages.success(request, f'Задача "{task.title}" создана.')
            return redirect('project_detail', pk=task.project.pk)
    else:
        form = TaskForm(user=request.user)
        if project_pk:
            form.initial['project'] = project_pk
    return render(request, 'tasks/task_form.html', {'form': form, 'title': 'Новая задача'})


@login_required
def task_detail(request, pk):
    task = get_object_or_404(Task, pk=pk)
    comments = task.comments.all().select_related('author', 'author__profile').order_by('created_at')

    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.task = task
            comment.author = request.user
            comment.save()
            messages.success(request, 'Комментарий добавлен!')
            return redirect('task_detail', pk=task.pk)  # ВАЖНО!
    else:
        form = CommentForm()

    context = {
        'task': task,
        'comments': comments,
        'form': form,
    }
    return render(request, 'tasks/task_detail.html', context)


@login_required
def task_edit(request, pk):
    task = get_object_or_404(Task, pk=pk)
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Задача обновлена.')
            return redirect('task_detail', pk=task.pk)
    else:
        form = TaskForm(instance=task, user=request.user)
    return render(request, 'tasks/task_form.html', {'form': form, 'title': 'Редактировать задачу'})


@login_required
def task_delete(request, pk):
    task = get_object_or_404(Task, pk=pk)
    project_pk = task.project.pk
    if request.method == 'POST':
        task.delete()
        messages.success(request, 'Задача удалена.')
        return redirect('project_detail', pk=project_pk)
    return render(request, 'tasks/task_delete.html', {'task': task})


# ─── COMMENTS ────────────────────────────────────────────

@login_required
@require_POST
def add_comment(request, task_pk):
    task = get_object_or_404(Task, pk=task_pk)
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.task = task
        comment.author = request.user
        comment.save()
    return redirect('task_detail', pk=task.pk)


# ─── AJAX: Update task status ────────────────────────────

@login_required
@require_POST
def task_update_status(request, pk):
    task = get_object_or_404(Task, pk=pk)
    new_status = request.POST.get('status')
    if new_status in dict(Task.STATUS_CHOICES):
        task.status = new_status
        task.save()
        return JsonResponse({'success': True, 'status': new_status})
    return JsonResponse({'success': False}, status=400)


# ─── ALL TASKS (my tasks view) ───────────────────────────

@login_required
def my_tasks(request):
    tasks = Task.objects.filter(assignee=request.user)
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
        form = UserEditForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, f'Данные пользователя "{user.get_full_name()}" обновлены.')
            return redirect('user_list')
    else:
        form = UserEditForm(instance=user)
    return render(request, 'tasks/user_form.html', {'form': form, 'title': f'Редактировать: {user.get_full_name()}'})


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
    # Получаем текущую дату или дату из параметра
    year = int(request.GET.get('year', timezone.now().year))
    month = int(request.GET.get('month', timezone.now().month))

    # Создаём календарь
    cal = calendar.monthcalendar(year, month)
    month_name = calendar.month_name[month]

    # Получаем ВСЕ задачи пользователя с дедлайнами
    # Не группируем - просто передаём список
    user_tasks = Task.objects.filter(
        assignee=request.user,
        due_date__isnull=False
    ).select_related('project')

    # Предыдущий и следующий месяц
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    context = {
        'calendar': cal,
        'year': year,
        'month': month,
        'month_name': month_name,
        'user_tasks': user_tasks,  # Просто список задач
        'prev_month': prev_month,
        'prev_year': prev_year,
        'next_month': next_month,
        'next_year': next_year,
        'today': timezone.now().date(),
    }

    return render(request, 'tasks/calendar.html', context)


@login_required
def kanban_view(request):
    """Kanban доска с задачами пользователя"""
    # Группируем задачи по статусам
    user_tasks = Task.objects.filter(
        Q(assignee=request.user) | Q(project__members=request.user)
    ).select_related('project', 'assignee').distinct()

    tasks_by_status = {
        'todo': user_tasks.filter(status='todo').order_by('-priority', 'due_date'),
        'in_progress': user_tasks.filter(status='in_progress').order_by('-priority', 'due_date'),
        'review': user_tasks.filter(status='review').order_by('-priority', 'due_date'),
        'done': user_tasks.filter(status='done').order_by('-updated_at')[:20],  # Показываем только последние 20
    }

    context = {
        'tasks_by_status': tasks_by_status,
        'total_tasks': user_tasks.count(),
    }

    return render(request, 'tasks/kanban.html', context)


@login_required
@require_POST
def kanban_update_status(request):
    """AJAX endpoint для обновления статуса задачи"""
    try:
        data = json.loads(request.body)
        task_id = data.get('task_id')
        new_status = data.get('status')

        # Проверяем что статус валидный
        valid_statuses = ['todo', 'in_progress', 'review', 'done']
        if new_status not in valid_statuses:
            return JsonResponse({'error': 'Invalid status'}, status=400)

        # Получаем задачу
        task = get_object_or_404(Task, pk=task_id)

        # Проверяем права доступа
        if task.assignee != request.user and request.user not in task.project.members.all():
            return JsonResponse({'error': 'Permission denied'}, status=403)

        # Обновляем статус
        task.status = new_status
        task.save()

        return JsonResponse({
            'success': True,
            'task_id': task.id,
            'new_status': new_status,
            'status_display': task.get_status_display()
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


