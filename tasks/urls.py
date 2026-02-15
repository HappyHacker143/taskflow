from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    path('', views.dashboard, name='home'),

    # Projects
    path('projects/', views.project_list, name='project_list'),
    path('projects/create/', views.project_create, name='project_create'),
    path('projects/<int:pk>/', views.project_detail, name='project_detail'),
    path('projects/<int:pk>/edit/', views.project_edit, name='project_edit'),
    path('projects/<int:pk>/delete/', views.project_delete, name='project_delete'),

    # Tasks
    path('tasks/create/', views.task_create, name='task_create'),
    path('tasks/create/<int:project_pk>/', views.task_create, name='task_create_in_project'),
    path('tasks/<int:pk>/', views.task_detail, name='task_detail'),
    path('tasks/<int:pk>/edit/', views.task_edit, name='task_edit'),
    path('tasks/<int:pk>/delete/', views.task_delete, name='task_delete'),
    path('tasks/<int:pk>/update-status/', views.task_update_status, name='task_update_status'),

    # Comments
    path('tasks/<int:task_pk>/comment/', views.add_comment, name='add_comment'),

    # My tasks
    path('my-tasks/', views.my_tasks, name='my_tasks'),

    # User Management (Admin only)
    path('users/', views.user_list, name='user_list'),
    path('users/create/', views.user_create, name='user_create'),
    path('users/<int:pk>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:pk>/delete/', views.user_delete, name='user_delete'),
    path('departments/', views.department_list, name='department_list'),
]
