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
    user = request.user
    projects = Project.objects.filter(
        Q(created_by=user) | Q(members=user)
    ).distinct()

    my_tasks = Task.objects.filter(assignee=user).order_by('-created_at')[:10]

    # Stats
    total_tasks = Task.objects.filter(
        Q(project__created_by=user) | Q(project__members=user)
    ).distinct().count()
    done_tasks = Task.objects.filter(
        Q(project__created_by=user) | Q(project__members=user),
        status='done'
    ).distinct().count()
    in_progress_tasks = Task.objects.filter(
        Q(project__created_by=user) | Q(project__members=user),
        status='in_progress'
    ).distinct().count()
    overdue_tasks = [t for t in Task.objects.filter(
        Q(project__created_by=user) | Q(project__members=user)
    ).exclude(status='done') if t.is_overdue]

    context = {
        'projects': projects,
        'my_tasks': my_tasks,
        'stats': {
            'total': total_tasks,
            'done': done_tasks,
            'in_progress': in_progress_tasks,
            'overdue': len(overdue_tasks),
        }
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
    comments = task.comments.all()
    comment_form = CommentForm()
    return render(request, 'tasks/task_detail.html', {
        'task': task,
        'comments': comments,
        'comment_form': comment_form,
    })


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
