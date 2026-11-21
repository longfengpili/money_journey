import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.db import DatabaseError
from django.test import TestCase

from accounts.models import UserProfile


class MemberApiTests(TestCase):
    def test_registration_requires_approval_and_profile_failure_rolls_back(self):
        data = {'username': 'new_member', 'first_name': '新成员',
                'password1': 'Safe-long-password-963!',
                'password2': 'Safe-long-password-963!'}
        response = self.client.post('/api/v1/auth/register/', json.dumps(data),
                                    content_type='application/json')
        self.assertEqual(response.status_code, 201)
        user = User.objects.get(username='new_member')
        self.assertFalse(user.userprofile.is_approved)
        data['username'] = 'rollback_member'
        with patch('accounts.models.UserProfile.objects.create',
                   side_effect=DatabaseError('fixture')), self.assertLogs(
                       'money_journey.api.base', level='ERROR'):
            response = self.client.post('/api/v1/auth/register/',
                                        json.dumps(data),
                                        content_type='application/json')
        self.assertEqual(response.status_code, 500)
        self.assertFalse(User.objects.filter(username='rollback_member').exists())

    def test_manager_creates_unusable_account_and_approves_registration(self):
        manager = User.objects.create_user('manager')
        UserProfile.objects.create(user=manager, is_approved=True,
                                   is_family_admin=True)
        self.client.force_login(manager)
        response = self.client.post('/api/v1/members/', json.dumps({
            'username': 'father', 'first_name': '父亲',
            'is_superuser': True,
        }), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        user = User.objects.get(username='father')
        self.assertFalse(user.has_usable_password())
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.userprofile.is_approved)
        user.userprofile.is_approved = False
        user.userprofile.save()
        self.assertEqual(self.client.post(f'/api/v1/approvals/{user.pk}/')
                         .status_code, 200)
        self.client.force_login(user)
        self.assertEqual(self.client.get('/api/v1/members/').status_code, 403)
