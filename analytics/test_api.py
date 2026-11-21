from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import UserProfile
from funds.models import FundRecord, FundSnapshot


class AnalyticsApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('member')
        UserProfile.objects.create(user=self.user, is_approved=True)
        self.other = User.objects.create_user('other')
        for user, amount in ((self.user, '12.34'), (self.other, '5.67')):
            FundRecord.objects.create(user=user, bank='ICBC',
                                      category='CURRENT', amount=amount)

    def test_guest_only_gets_demo_and_member_gets_decimal_strings(self):
        response = self.client.get('/api/v1/analytics/summary/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['demo'])
        self.client.force_login(self.user)
        data = self.client.get('/api/v1/analytics/summary/').json()
        self.assertEqual(data['total_amount'], '18.01')
        self.assertEqual(data['total_records'], 2)
        filtered = self.client.get('/api/v1/analytics/summary/', {
            'owner_id': self.user.pk,
        }).json()
        self.assertEqual(filtered['total_amount'], '12.34')

    def test_owner_id_selects_renamed_history_and_revoked_access_is_denied(self):
        FundSnapshot.objects.create(user=self.user, owner='old',
                                    created_by=self.other,
                                    snapshot_date=date(2026, 11, 20),
                                    total_amount='12.34', record_count=1)
        self.client.force_login(self.user)
        data = self.client.get('/api/v1/analytics/trend/', {
            'owner_id': self.user.pk,
        }).json()
        self.assertEqual(data['results'][0]['total_amount'], '12.34')
        self.user.userprofile.is_approved = False
        self.user.userprofile.save()
        self.assertEqual(self.client.get('/api/v1/analytics/summary/')
                         .status_code, 403)
