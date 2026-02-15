from django.contrib import admin
from .models import Project, Task, TaskComment, Department, UserProfile


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name', 'description']


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'department', 'position', 'role']
    list_filter = ['department', 'role']
    search_fields = ['user__first_name', 'user__last_name', 'position']


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_by', 'task_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'description']


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'project', 'status', 'priority', 'assignee', 'due_date', 'created_at']
    list_filter = ['status', 'priority', 'project', 'due_date']
    search_fields = ['title', 'description', 'tags']
    ordering = ['-created_at']


@admin.register(TaskComment)
class TaskCommentAdmin(admin.ModelAdmin):
    list_display = ['task', 'author', 'created_at']
    list_filter = ['created_at']
