from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from funds.models import FundRecord


class FamilyAnalyticsTests(TestCase):
    def test_shared_totals_follow_account_after_rename(self):
        viewer = User.objects.create_user('viewer')
        UserProfile.objects.create(user=viewer, is_approved=True)
        owner = User.objects.create_user('old', first_name='母亲')
        first = FundRecord.objects.create(
            user=owner,
            bank='ICBC',
            category='CURRENT',
            amount=100,
        )
        owner.username = 'new'
        owner.save()
        FundRecord.objects.create(
            user=owner,
            bank='ICBC',
            category='CURRENT',
            amount=200,
        )
        FundRecord.objects.create(
            owner='legacy',
            bank='ICBC',
            category='CURRENT',
            amount=50,
        )
        self.client.force_login(viewer)
        response = self.client.get(reverse('analytics:dashboard'))
        self.assertEqual(response.context['total_amount'], 350)
        self.assertEqual(response.context['owner_count'], 2)
        summary = response.context['owner_summary'][0]
        self.assertEqual(summary['owner'], 'new')
        self.assertEqual(summary['first_name'], '母亲')
        self.assertEqual(summary['total_amount'], 300)
        filtered = self.client.get(
            reverse('analytics:dashboard'), {'owner': 'new'}
        )
        self.assertEqual(filtered.context['total_amount'], 300)
        charts = self.client.get(reverse('analytics:charts'))
        self.assertEqual(charts.context['owner_labels'], ['母亲', 'legacy'])
        self.assertEqual(charts.context['owner_totals'], [300, 50])
        self.assertContains(
            self.client.get(reverse('funds:record_list')), '母亲'
        )
        first.refresh_from_db()
        self.assertEqual(first.owner, 'old')
