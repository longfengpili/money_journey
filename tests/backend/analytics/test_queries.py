"""统一统计查询的筛选、金额及历史归属回归。"""

from datetime import date
from decimal import Decimal
from unittest import skipIf

from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase

from analytics.queries import (
    get_owner_choices,
    get_snapshot_trend,
    normalize_filters,
    summarize_assets,
)
from funds.models import FundRecord, FundSnapshot


class AssetSummaryTests(TestCase):
    def setUp(self):
        self.first = User.objects.create_user('first', first_name='家人')
        self.second = User.objects.create_user('second', first_name='家人')
        for user, bank, category, amount, status in (
            (self.first, 'ICBC', 'CURRENT', '10.10', 'ACTIVE'),
            (self.first, 'CCB', 'SAVINGS', '20.20', 'ACTIVE'),
            (self.second, 'ICBC', 'CURRENT', '10.10', 'ACTIVE'),
            (self.second, 'CCB', 'SAVINGS', '99.99', 'WITHDRAWN'),
            (None, 'ICBC', 'CURRENT', '0.00', 'ACTIVE'),
        ):
            FundRecord.objects.create(
                user=user, owner='first', bank=bank, category=category,
                amount=Decimal(amount), savings_status=status,
            )

    def test_default_and_explicit_all_status_have_different_totals(self):
        self.assertEqual(normalize_filters({})['savings_status'], 'ACTIVE')
        self.assertEqual(summarize_assets()['total_amount'], Decimal('40.40'))
        result = summarize_assets({'savings_status': ' '})
        self.assertEqual(result['total_amount'], Decimal('140.39'))
        self.assertEqual(result['total_records'], 5)

    def test_all_dimensions_share_amount_and_count_from_one_query(self):
        with self.assertNumQueries(1):
            result = summarize_assets()
        self.assertEqual(result['total_records'], 4)
        self.assertEqual(result['owner_count'], 3)
        for dimension in ('owner', 'bank', 'category', 'status'):
            rows = result[dimension + '_summary']
            self.assertEqual(
                sum(row['total_amount'] for row in rows), Decimal('40.40')
            )
            self.assertEqual(sum(row['record_count'] for row in rows), 4)
        self.assertEqual(
            [(row['owner'], row['first_name'], row['total_amount'])
             for row in result['owner_summary']],
            [('first', '家人', Decimal('30.30')),
             ('second', '家人', Decimal('10.10')),
             ('first', 'first', Decimal('0.00'))],
        )

    def test_combined_filters_keep_partial_owner_and_exact_codes(self):
        filters = {'owner': ' fir ', 'bank': ' ICBC ', 'category': 'CURRENT'}
        result = summarize_assets(filters)
        self.assertEqual(result['total_amount'], Decimal('10.10'))
        self.assertEqual(result['total_records'], 2)
        self.assertEqual(summarize_assets({'bank': 'IC'})['total_records'], 0)
        self.assertEqual(
            summarize_assets({'savings_status': 'UNKNOWN'})['total_records'], 0
        )

    def test_empty_results_have_decimal_zero_and_empty_dimensions(self):
        result = summarize_assets({'owner': 'missing'})
        self.assertEqual(result['total_amount'], Decimal('0'))
        self.assertIsInstance(result['total_amount'], Decimal)
        self.assertEqual(result['total_records'], 0)
        self.assertEqual(result['owner_count'], 0)
        for dimension in ('owner', 'bank', 'category', 'status'):
            self.assertEqual(result[dimension + '_summary'], [])

    @skipIf(connection.vendor == 'sqlite', 'SQLite SUM 不保证大额小数精度')
    def test_large_grouped_amount_keeps_cents_on_mysql(self):
        FundRecord.objects.create(
            user=self.first, bank='ICBC', category='CURRENT',
            amount=Decimal('9999999999999.99'),
        )
        result = summarize_assets()
        self.assertEqual(result['total_amount'], Decimal('10000000000040.39'))
        self.assertIsInstance(result['total_amount'], Decimal)

    def test_large_separate_groups_keep_decimal_total(self):
        FundRecord.objects.create(
            user=self.first, bank='ABC', category='CURRENT',
            amount=Decimal('9999999999999.99'),
        )
        self.assertEqual(
            summarize_assets()['total_amount'], Decimal('10000000000040.39')
        )

    def test_owner_choices_include_finished_records_and_blank_names(self):
        finished = User.objects.create_user('finished', first_name='  ')
        FundRecord.objects.create(
            user=finished, bank='CCB', category='CURRENT',
            amount=1, savings_status='WITHDRAWN',
        )
        choices = get_owner_choices()
        self.assertIn(('finished', 'finished'), choices)
        self.assertIn(('first', '家人'), choices)
        self.assertIn(('first', 'first'), choices)
        FundRecord.objects.create(bank='ICBC', category='CURRENT', amount=0)
        summary = summarize_assets()['owner_summary']
        self.assertIn('待核对所有者', [row['first_name'] for row in summary])

    def test_equal_totals_have_stable_code_order(self):
        FundRecord.objects.all().update(amount=0)
        result = summarize_assets()
        self.assertEqual(
            [row['bank'] for row in result['bank_summary']], ['CCB', 'ICBC']
        )
        self.assertEqual(
            [row['category'] for row in result['category_summary']],
            ['CURRENT', 'SAVINGS'],
        )


class SnapshotTrendTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('before', first_name='同名')
        self.other = User.objects.create_user('other', first_name='同名')
        for user, owner, day, amount in (
            (self.owner, 'before', 20, 10),
            (self.owner, 'before', 21, 20),
            (self.other, 'after', 20, 100),
            (None, 'legacy', 20, 5),
        ):
            FundSnapshot.objects.create(
                user=user, owner=owner, created_by=self.other,
                snapshot_date=date(2026, 11, day), total_amount=amount,
                record_count=1, bank_summary={'ICBC': amount},
            )
        self.owner.username = 'after'
        self.owner.save()

    def test_current_username_finds_linked_history_after_rename(self):
        with self.assertNumQueries(1):
            rows = get_snapshot_trend(' aft ')
        self.assertEqual(
            rows,
            [{'snapshot_date': date(2026, 11, 20),
              'total_amount': Decimal('10')},
             {'snapshot_date': date(2026, 11, 21),
              'total_amount': Decimal('20')}],
        )
        self.assertEqual(get_snapshot_trend('before'), [])

    def test_unlinked_legacy_uses_text_and_total_groups_by_day(self):
        self.assertEqual(get_snapshot_trend('legacy')[0]['total_amount'], 5)
        self.assertEqual(
            [row['total_amount'] for row in get_snapshot_trend()], [115, 20]
        )
        self.assertEqual(get_snapshot_trend('missing'), [])
