"""页面统计与图表 JSON 数据的集成回归。"""

import json
import re
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from funds.models import FundRecord, FundSnapshot


class AnalyticsPageTests(TestCase):
    def setUp(self):
        self.member = User.objects.create_user('before', first_name='成员')
        UserProfile.objects.create(user=self.member, is_approved=True)
        self.other = User.objects.create_user('other')
        for user, bank, category, amount, status in (
            (self.member, 'ICBC', 'CURRENT', '12.34', 'ACTIVE'),
            (self.other, 'CCB', 'SAVINGS', '0.01', 'ACTIVE'),
            (self.member, 'ICBC', 'CURRENT', '999', 'WITHDRAWN'),
        ):
            FundRecord.objects.create(
                user=user, bank=bank, category=category,
                amount=amount, savings_status=status,
            )
        self.client.force_login(self.member)

    def chart_data(self, response):
        self.assertEqual(response.status_code, 200)
        match = re.search(
            r'<script[^>]*id="analytics-chart-data"[^>]*>(.*?)</script>',
            response.content.decode(), re.DOTALL,
        )
        self.assertIsNotNone(match, '页面需要提供独立 JSON 图表数据')
        return json.loads(match.group(1))

    def test_both_pages_use_same_active_totals(self):
        dashboard = self.client.get(reverse('analytics:dashboard'))
        charts = self.client.get(reverse('analytics:charts'))
        first, second = self.chart_data(dashboard), self.chart_data(charts)
        self.assertEqual(dashboard.context['total_amount'], Decimal('12.35'))
        for dimension in ('owner', 'bank', 'category'):
            self.assertEqual(first[dimension + '_labels'],
                             second[dimension + '_labels'])
            self.assertEqual(first[dimension + '_totals'], [12.34, 0.01])
            self.assertEqual(first[dimension + '_totals'],
                             second[dimension + '_totals'])

    def test_special_names_round_trip_without_executable_markup(self):
        name = '家人\'"\n</script><script>alert("name")</script>&'
        self.member.first_name = name
        self.member.save()
        for route in ('analytics:dashboard', 'analytics:charts'):
            response = self.client.get(reverse(route))
            payload = self.chart_data(response)
            self.assertEqual(payload['owner_labels'][0], name)
            self.assertNotIn(name, response.content.decode())
            self.assertNotContains(response, '<script>alert("name")</script>')

    def test_renamed_owner_trend_uses_account_and_preserves_history(self):
        snapshot = FundSnapshot.objects.create(
            user=self.member, owner='before', created_by=self.other,
            snapshot_date=date(2026, 11, 20), total_amount='7.89',
            record_count=1, bank_summary={'ICBC': 7.89},
        )
        self.member.username = 'after'
        self.member.save()
        response = self.client.get(reverse('analytics:dashboard'), {
            'owner': 'after', 'bank': 'CCB', 'savings_status': 'WITHDRAWN',
        })
        self.assertEqual(response.context['total_amount'], 0)
        payload = self.chart_data(response)
        self.assertEqual(payload['snapshot_dates'], ['2026-11-20'])
        self.assertEqual(payload['snapshot_totals'], [7.89])
        self.assertContains(response, '仅跟随所有者筛选')
        snapshot.refresh_from_db()
        self.assertEqual(snapshot.owner, 'before')
        self.assertEqual(snapshot.bank_summary, {'ICBC': 7.89})

    def test_explicit_all_status_affects_live_stats(self):
        response = self.client.get(reverse('analytics:dashboard'), {
            'owner': 'before', 'savings_status': '',
        })
        self.assertEqual(response.context['total_amount'], Decimal('1011.34'))
        self.assertEqual(response.context['total_records'], 2)
        self.assertEqual(response.context['filter_form']['savings_status'], '')

    def test_partial_and_history_only_owner_filters_survive_form_submission(
        self,
    ):
        FundSnapshot.objects.create(
            user=self.other, owner='old_other', created_by=self.member,
            snapshot_date=date(2026, 11, 20), total_amount=10, record_count=1,
        )
        FundSnapshot.objects.create(
            user=self.member, owner='before', created_by=self.member,
            snapshot_date=date(2026, 11, 20), total_amount=1, record_count=1,
        )
        FundRecord.objects.filter(user=self.other).update(user=self.member)
        for owner in ('bef', 'other'):
            response = self.client.get(reverse('analytics:dashboard'), {
                'owner': owner,
            })
            self.assertIsNotNone(re.search(
                r'<option[^>]*value="' + owner + r'"[^>]*selected',
                response.content.decode(),
            ), '当前所有者筛选必须保持选中')
            self.assertContains(response, owner + ' 的资金快照历史趋势')
        FundRecord.objects.create(
            owner='before', bank='ICBC', category='CURRENT', amount=0,
        )
        response = self.client.get(reverse('analytics:dashboard'), {
            'owner': 'before',
        })
        self.assertEqual(response.content.decode().count('的资金快照历史趋势'), 1)

    def test_empty_filter_result_and_absent_snapshots_are_usable(self):
        response = self.client.get(reverse('analytics:dashboard'), {
            'owner': 'missing',
        })
        payload = self.chart_data(response)
        self.assertEqual(payload['bank_totals'], [])
        self.assertEqual(payload['snapshot_totals'], [])
        self.assertFalse(response.context['has_snapshots'])
        self.assertNotContains(response, 'id="snapshotChart"')

    def test_guest_demo_uses_json_and_ignores_real_assets(self):
        self.client.logout()
        response = self.client.get(reverse('analytics:dashboard'), {
            'owner': 'before', 'bank': 'ICBC',
        })
        payload = self.chart_data(response)
        self.assertEqual(response.context['total_amount'], 1280000)
        self.assertEqual(
            payload['category_totals'], [680000, 320000, 180000, 100000]
        )
        self.assertEqual(payload['snapshot_totals'], [])
        self.assertEqual(response.context['filter_form']['owner'], '')
        self.assertEqual(
            self.client.get(reverse('analytics:charts')).status_code, 302
        )
