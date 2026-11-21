"""新前端身份接口的会话、审批和 CSRF 回归。"""

import json

from django.contrib.auth.models import User
from django.test import Client, TestCase

from accounts.models import UserProfile


class AuthApiTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.user = User.objects.create_user('member', password='test-secret')
        UserProfile.objects.create(user=self.user, is_approved=True)

    def post(self, path, data, token=None):
        return self.client.post(
            '/api/v1/auth/' + path + '/', json.dumps(data),
            content_type='application/json',
            **({'HTTP_X_CSRFTOKEN': token} if token else {}),
        )

    def test_guest_context_and_login_require_csrf_then_rotate_token(self):
        response = self.client.get('/api/v1/auth/context/')
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()['user'])
        token = response.json()['csrf_token']
        data = {'username': 'member', 'password': 'test-secret'}
        self.assertEqual(self.post('login', data).status_code, 403)
        result = self.post('login', data, token)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()['user']['id'], self.user.pk)
        self.assertNotEqual(result.json()['csrf_token'], token)
        self.assertEqual(self.post('logout', {}, token).status_code, 403)
        self.assertEqual(self.post('logout', {}, result.json()['csrf_token'])
                         .status_code, 200)
        self.assertIsNone(self.client.get('/api/v1/auth/context/').json()['user'])

    def test_unapproved_login_does_not_create_authenticated_session(self):
        self.user.userprofile.is_approved = False
        self.user.userprofile.save()
        token = self.client.get('/api/v1/auth/context/').json()['csrf_token']
        response = self.post('login', {
            'username': 'member', 'password': 'test-secret',
        }, token)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['code'], 'APPROVAL_PENDING')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_existing_session_rechecks_approval_and_staff_is_not_admin(self):
        self.client.force_login(self.user)
        self.assertFalse(self.client.get('/api/v1/auth/context/')
                         .json()['capabilities']['manage_family'])
        self.user.userprofile.is_approved = False
        self.user.userprofile.save()
        data = self.client.get('/api/v1/auth/context/').json()
        self.assertFalse(data['capabilities']['write_assets'])
