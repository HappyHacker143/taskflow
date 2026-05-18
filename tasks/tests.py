from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .forms import TaskForm
from .models import Project, Task, TaskActivity


@override_settings(MEDIA_ROOT='/tmp/taskflow-test-media')
class PermissionTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('owner', password='pass12345')
        self.member = User.objects.create_user('member', password='pass12345')
        self.outsider = User.objects.create_user('outsider', password='pass12345')
        self.admin = User.objects.create_user('admin', password='pass12345', is_superuser=True, is_staff=True)
        self.admin.profile.role = 'admin'
        self.admin.profile.save()
        self.project = Project.objects.create(name='Secret', created_by=self.owner)
        self.project.members.add(self.owner, self.member)
        self.task = Task.objects.create(
            project=self.project,
            title='Private task',
            created_by=self.owner,
            assignee=self.member,
        )

    def test_outsider_cannot_view_project(self):
        self.client.login(username='outsider', password='pass12345')
        response = self.client.get(reverse('project_detail', args=[self.project.pk]))
        self.assertEqual(response.status_code, 404)

    def test_member_can_view_project(self):
        self.client.login(username='member', password='pass12345')
        response = self.client.get(reverse('project_detail', args=[self.project.pk]))
        self.assertEqual(response.status_code, 200)

    def test_outsider_cannot_update_task_status(self):
        self.client.login(username='outsider', password='pass12345')
        response = self.client.post(reverse('task_update_status', args=[self.task.pk]), {'status': 'done'})
        self.assertEqual(response.status_code, 404)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'todo')

    def test_assignee_can_update_task_status_and_activity_is_logged(self):
        self.client.login(username='member', password='pass12345')
        response = self.client.post(reverse('task_update_status', args=[self.task.pk]), {'status': 'in_progress'})
        self.assertEqual(response.status_code, 200)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'in_progress')
        self.assertTrue(TaskActivity.objects.filter(task=self.task, action=TaskActivity.ACTION_STATUS_CHANGED).exists())

    def test_admin_can_view_any_project(self):
        self.client.login(username='admin', password='pass12345')
        response = self.client.get(reverse('project_detail', args=[self.project.pk]))
        self.assertEqual(response.status_code, 200)


class TaskFormTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('owner', password='pass12345')
        self.member = User.objects.create_user('member', password='pass12345')
        self.outsider = User.objects.create_user('outsider', password='pass12345')
        self.project = Project.objects.create(name='Project', created_by=self.owner)
        self.project.members.add(self.owner, self.member)

    def test_assignee_must_be_project_member(self):
        form = TaskForm(
            data={
                'title': 'Task',
                'description': '',
                'project': self.project.pk,
                'status': 'todo',
                'priority': 'medium',
                'assignee': self.outsider.pk,
                'due_date': '',
                'tags': '',
            },
            user=self.owner,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('assignee', form.errors)


@override_settings(MEDIA_ROOT='/tmp/taskflow-test-media')
class CommentUploadTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('owner', password='pass12345')
        self.project = Project.objects.create(name='Project', created_by=self.owner)
        self.project.members.add(self.owner)
        self.task = Task.objects.create(project=self.project, title='Task', created_by=self.owner, assignee=self.owner)

    def test_comment_rejects_disallowed_attachment(self):
        self.client.login(username='owner', password='pass12345')
        upload = SimpleUploadedFile('payload.svg', b'<svg></svg>', content_type='image/svg+xml')
        response = self.client.post(
            reverse('add_comment', args=[self.task.pk]),
            {'text': 'bad file', 'attachment': upload},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.task.comments.count(), 0)
