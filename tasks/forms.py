from django import forms
from django.contrib.auth.models import User
from .models import Project, Task, TaskComment, Department, UserProfile


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'description', 'color', 'members']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Название проекта'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'Описание проекта'}),
            'color': forms.TextInput(attrs={'class': 'form-input color-input', 'type': 'color'}),
            'members': forms.SelectMultiple(attrs={'class': 'form-input select-multiple'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Показываем пользователей с полными именами
        self.fields['members'].queryset = User.objects.filter(is_active=True).order_by('first_name', 'last_name')
        self.fields['members'].label_from_instance = lambda obj: f"{obj.first_name} {obj.last_name} ({obj.profile.position or 'Сотрудник'})"


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'project', 'status', 'priority', 'assignee', 'due_date', 'tags']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Название задачи'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'Описание задачи'}),
            'project': forms.Select(attrs={'class': 'form-input'}),
            'status': forms.Select(attrs={'class': 'form-input'}),
            'priority': forms.Select(attrs={'class': 'form-input'}),
            'assignee': forms.Select(attrs={'class': 'form-input'}),
            'due_date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'tags': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'frontend, urgent, api'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            # Показываем только проекты, где пользователь участник или создатель
            from django.db.models import Q
            self.fields['project'].queryset = Project.objects.filter(
                Q(created_by=user) | Q(members=user)
            ).distinct()
            
            # Показываем активных пользователей с полными именами
            self.fields['assignee'].queryset = User.objects.filter(is_active=True).order_by('first_name', 'last_name')
            self.fields['assignee'].label_from_instance = lambda obj: f"{obj.first_name} {obj.last_name} - {obj.profile.position or 'Сотрудник'}"
            self.fields['assignee'].required = False


class CommentForm(forms.ModelForm):
    class Meta:
        model = TaskComment
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={'class': 'form-input', 'rows': 2, 'placeholder': 'Напишите комментарий...'}),
        }


class UserCreateForm(forms.ModelForm):
    """Форма создания пользователя администратором"""
    password1 = forms.CharField(
        label='Пароль', 
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Пароль'})
    )
    password2 = forms.CharField(
        label='Повторите пароль', 
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Повторите пароль'})
    )
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        required=False,
        label='Отдел',
        widget=forms.Select(attrs={'class': 'form-input'})
    )
    position = forms.CharField(
        max_length=200,
        required=False,
        label='Должность',
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Разработчик'})
    )
    role = forms.ChoiceField(
        choices=UserProfile.ROLE_CHOICES,
        initial='employee',
        label='Роль',
        widget=forms.Select(attrs={'class': 'form-input'})
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        label='Телефон',
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': '+7 (999) 123-45-67'})
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Логин'}),
            'email': forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'email@company.com'}),
            'first_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Имя'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Фамилия'}),
        }

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('Пароли не совпадают.')
        return password2

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError('Пользователь с таким email уже существует.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
            # Обновляем профиль
            profile = user.profile
            profile.department = self.cleaned_data.get('department')
            profile.position = self.cleaned_data.get('position')
            profile.role = self.cleaned_data.get('role')
            profile.phone = self.cleaned_data.get('phone')
            profile.save()
        return user


class UserEditForm(forms.ModelForm):
    """Форма редактирования пользователя администратором"""
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        required=False,
        label='Отдел',
        widget=forms.Select(attrs={'class': 'form-input'})
    )
    position = forms.CharField(
        max_length=200,
        required=False,
        label='Должность',
        widget=forms.TextInput(attrs={'class': 'form-input'})
    )
    role = forms.ChoiceField(
        choices=UserProfile.ROLE_CHOICES,
        label='Роль',
        widget=forms.Select(attrs={'class': 'form-input'})
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        label='Телефон',
        widget=forms.TextInput(attrs={'class': 'form-input'})
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'is_active']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and hasattr(self.instance, 'profile'):
            profile = self.instance.profile
            self.fields['department'].initial = profile.department
            self.fields['position'].initial = profile.position
            self.fields['role'].initial = profile.role
            self.fields['phone'].initial = profile.phone

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit and hasattr(user, 'profile'):
            profile = user.profile
            profile.department = self.cleaned_data.get('department')
            profile.position = self.cleaned_data.get('position')
            profile.role = self.cleaned_data.get('role')
            profile.phone = self.cleaned_data.get('phone')
            profile.save()
        return user
