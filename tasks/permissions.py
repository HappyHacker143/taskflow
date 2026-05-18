from django.db.models import Q

from .models import Project, Task


ADMIN_ROLES = {'admin'}
MANAGER_ROLES = {'admin', 'manager', 'team_lead'}


def user_role(user):
    if not user.is_authenticated:
        return None
    profile = getattr(user, 'profile', None)
    return getattr(profile, 'role', None)


def is_admin(user):
    return user.is_authenticated and (user.is_superuser or user_role(user) in ADMIN_ROLES)


def is_manager(user):
    return user.is_authenticated and (user.is_superuser or user_role(user) in MANAGER_ROLES)


def project_visibility_q(user):
    if is_admin(user):
        return Q()
    if is_manager(user):
        return Q(created_by=user) | Q(members=user)
    return Q(created_by=user) | Q(members=user) | Q(tasks__assignee=user)


def visible_projects(user):
    queryset = Project.objects.filter(is_archived=False)
    if is_admin(user):
        return queryset
    return queryset.filter(project_visibility_q(user)).distinct()


def editable_projects(user):
    queryset = Project.objects.filter(is_archived=False)
    if is_admin(user):
        return queryset
    if is_manager(user):
        return queryset.filter(Q(created_by=user) | Q(members=user)).distinct()
    return queryset.filter(created_by=user)


def can_view_project(user, project):
    if not user.is_authenticated or project.is_archived:
        return False
    if is_admin(user):
        return True
    return (
        project.created_by_id == user.id
        or project.members.filter(pk=user.pk).exists()
        or project.tasks.filter(assignee=user).exists()
    )


def can_edit_project(user, project):
    if not user.is_authenticated or project.is_archived:
        return False
    if is_admin(user):
        return True
    if is_manager(user):
        return project.created_by_id == user.id or project.members.filter(pk=user.pk).exists()
    return project.created_by_id == user.id


def task_visibility_q(user):
    if is_admin(user):
        return Q()
    if is_manager(user):
        return Q(created_by=user) | Q(assignee=user) | Q(project__created_by=user) | Q(project__members=user)
    return Q(assignee=user) | Q(created_by=user) | Q(project__members=user)


def visible_tasks(user):
    queryset = Task.objects.filter(is_archived=False, project__is_archived=False)
    if is_admin(user):
        return queryset
    return queryset.filter(task_visibility_q(user)).distinct()


def editable_tasks(user):
    queryset = Task.objects.filter(is_archived=False, project__is_archived=False)
    if is_admin(user):
        return queryset
    if is_manager(user):
        return queryset.filter(
            Q(created_by=user) | Q(assignee=user) | Q(project__created_by=user) | Q(project__members=user)
        ).distinct()
    return queryset.filter(Q(created_by=user) | Q(assignee=user)).distinct()


def can_view_task(user, task):
    if not user.is_authenticated or task.is_archived or task.project.is_archived:
        return False
    if is_admin(user):
        return True
    return (
        task.created_by_id == user.id
        or task.assignee_id == user.id
        or task.project.created_by_id == user.id
        or task.project.members.filter(pk=user.pk).exists()
    )


def can_edit_task(user, task):
    if not user.is_authenticated or task.is_archived or task.project.is_archived:
        return False
    if is_admin(user):
        return True
    if is_manager(user):
        return (
            task.created_by_id == user.id
            or task.assignee_id == user.id
            or task.project.created_by_id == user.id
            or task.project.members.filter(pk=user.pk).exists()
        )
    return task.created_by_id == user.id or task.assignee_id == user.id
