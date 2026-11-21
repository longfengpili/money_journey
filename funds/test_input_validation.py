import io
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import DatabaseError
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from accounts.models import UserProfile
from funds.forms import FundRecordForm
from funds.importers import import_fund_csv
from funds.models import FundRecord


class FundInputTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('member')
        UserProfile.objects.create(user=self.user, is_approved=True)
        self.data = {'bank': 'ICBC', 'category': 'CURRENT', 'amount': '0'}
        self.client.force_login(self.user)

    def upload(self, text):
        return SimpleUploadedFile('assets.csv', text.encode('utf-8-sig'))

    def test_form_accepts_zero_and_exact_decimal_and_optional_fields(self):
        for amount in ('0', '0.10', '9999999999999.99'):
            with self.subTest(amount=amount):
                form = FundRecordForm(
                    {**self.data, 'amount': amount, 'savings_status': ''},
                    actor=self.user,
                )
                self.assertTrue(form.is_valid(), form.errors)
                record = form.save()
                record.refresh_from_db()
                self.assertEqual(record.amount, Decimal(amount))
                self.assertEqual(record.savings_status, 'ACTIVE')
                self.assertEqual(record.created_by, self.user)

    def test_shared_invalid_fields_are_rejected_by_form_and_csv(self):
        values = (
            ('amount', '-1'),
            ('amount', 'NaN'),
            ('amount', 'Infinity'),
            ('amount', '1.001'),
            ('amount', '10000000000000'),
            ('interest_rate', '-1'),
            ('interest_rate', 'NaN'),
            ('interest_rate', '1.001'),
            ('deposit_period', '0'),
            ('deposit_period', 'abc'),
            ('deposit_period', '1.5'),
            ('bank', 'UNKNOWN'),
            ('category', 'UNKNOWN'),
            ('savings_status', 'UNKNOWN'),
            ('due_date', '2026-02-30'),
        )
        for field, value in values:
            with self.subTest(field=field, value=value):
                data = {**self.data, field: value}
                form = FundRecordForm(data, actor=self.user)
                self.assertFalse(form.is_valid())
                self.assertIn(field, form.errors)
                text = ','.join(data) + '\n' + ','.join(data.values()) + '\n'
                result = import_fund_csv(self.upload(text), actor=self.user)
                self.assertEqual(result.success_count, 0)
                self.assertEqual(result.error_count, 1)
                self.assertIn(field, result.errors[0])
        self.assertEqual(FundRecord.objects.count(), 0)

    def test_dates_and_derived_fields_are_shared(self):
        for value in ('2029-11-21', '2029/11/21', '20291121'):
            form = FundRecordForm(
                {
                    **self.data,
                    'due_date': value,
                    'deposit_period': '3',
                },
                actor=self.user,
            )
            self.assertTrue(form.is_valid(), form.errors)
            record = form.save()
            self.assertEqual(record.due_date, date(2029, 11, 21))
            self.assertEqual(record.due_month, '2029-11')
            old_start = record.start_date
            form = FundRecordForm(self.data, actor=self.user, instance=record)
            self.assertTrue(form.is_valid(), form.errors)
            updated = form.save()
            updated.refresh_from_db()
            self.assertIsNone(updated.due_month)
            self.assertEqual(updated.start_date, old_start)

    def test_csv_keeps_precision_chinese_choices_and_explicit_start_date(self):
        result = import_fund_csv(
            self.upload(
                'bank,category,amount,interest_rate,start_date,due_date\n'
                '工商银行,活期存款,9999999999999.99,0,2026/11/21,20291121\n'
            ),
            actor=self.user,
        )
        self.assertEqual(result.success_count, 1)
        record = FundRecord.objects.get()
        self.assertEqual(record.amount, Decimal('9999999999999.99'))
        self.assertEqual(record.interest_rate, 0)
        self.assertEqual(record.start_date, date(2026, 11, 21))
        self.assertEqual(record.due_month, '2029-11')

    def test_csv_partial_validation_and_permission_errors(self):
        other = User.objects.create_user('other')
        result = import_fund_csv(
            self.upload(
                'bank,category,amount,owner\n'
                'icbc,CURRENT,0,member\n'
                'ICBC,CURRENT,-1,member\n'
                'ICBC,CURRENT,20,other\n'
            ),
            actor=self.user,
        )
        self.assertEqual(result.success_count, 1)
        self.assertEqual(result.error_count, 2)
        self.assertIn('第3行', result.errors[0])
        self.assertIn('owner', result.errors[1])
        self.assertFalse(FundRecord.objects.filter(user=other).exists())

    def test_file_errors_do_not_write_any_rows(self):
        valid = 'bank,category,amount\nICBC,CURRENT,0\n'
        for upload in (
            self.upload('bank,category\nICBC,CURRENT\n'),
            SimpleUploadedFile('assets.csv', b'\xff\xfe'),
        ):
            with self.assertRaises(ValidationError):
                import_fund_csv(upload, actor=self.user)
        with patch('funds.importers.MAX_ROWS', 1):
            with self.assertRaises(ValidationError):
                import_fund_csv(
                    self.upload(
                        valid + 'ICBC,CURRENT,1\n',
                    ),
                    actor=self.user,
                )
        with patch('funds.importers.MAX_FILE_SIZE', 1):
            with self.assertRaises(ValidationError):
                import_fund_csv(self.upload(valid), actor=self.user)
        self.assertEqual(FundRecord.objects.count(), 0)

    def test_csv_database_failure_rolls_back_previous_batch(self):
        text = 'bank,category,amount\n' + 'ICBC,CURRENT,0\n' * 101
        bulk_create = FundRecord.objects.bulk_create
        calls = 0

        def fail_second_batch(records, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise DatabaseError('测试第二批写入失败')
            return bulk_create(records, **kwargs)

        with patch(
            'funds.importers.FundRecord.objects.bulk_create',
            side_effect=fail_second_batch,
        ):
            with self.assertRaises(DatabaseError):
                import_fund_csv(self.upload(text), actor=self.user)
        self.assertEqual(calls, 2)
        self.assertEqual(FundRecord.objects.count(), 0)

    def test_page_keeps_invalid_input_and_reports_field_error(self):
        response = self.client.post(
            reverse('funds:add_record'),
            {
                **self.data,
                'amount': '12.345',
                'deposit_period': 'abc',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('amount', response.context['form'].errors)
        self.assertIn('deposit_period', response.context['form'].errors)
        self.assertContains(response, '12.345')
        self.assertContains(response, 'abc')
        self.assertEqual(FundRecord.objects.count(), 0)

    def test_edit_errors_keep_original_database_values(self):
        record = FundRecord.objects.create(
            user=self.user,
            bank='ICBC',
            category='CURRENT',
            amount=20,
        )
        response = self.client.post(
            reverse('funds:edit_record', args=[record.pk]),
            {**self.data, 'amount': '-1'},
        )
        self.assertEqual(response.status_code, 200)
        record.refresh_from_db()
        self.assertEqual(record.amount, 20)

    def test_downloaded_csv_template_can_be_imported(self):
        response = self.client.get(reverse('funds:download_csv_template'))
        result = import_fund_csv(
            SimpleUploadedFile(
                'template.csv',
                response.content,
            ),
            actor=self.user,
        )
        self.assertEqual(result.success_count, 1)
        self.assertEqual(result.error_count, 0)

    def test_partial_save_preserves_concurrent_date_change(self):
        record = FundRecord.objects.create(
            user=self.user,
            bank='ICBC',
            category='CURRENT',
            amount=20,
            due_date=date(2029, 11, 21),
        )
        FundRecord.objects.filter(pk=record.pk).update(
            due_date=date(2030, 1, 1),
            due_month='2030-01',
        )
        record.amount = 30
        record.save(update_fields=['amount'])
        record.refresh_from_db()
        self.assertEqual(record.due_date, date(2030, 1, 1))
        self.assertEqual(record.due_month, '2030-01')
        record.due_date = None
        record.save(update_fields=['due_date'])
        record.refresh_from_db()
        self.assertIsNone(record.due_month)

    def test_oversized_deposit_period_returns_validation_error(self):
        data = {
            **self.data,
            'deposit_period': '999999999',
            'due_date': '2029-11-21',
        }
        form = FundRecordForm(data, actor=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('deposit_period', form.errors)

    def test_csv_reuses_owner_resolution_for_repeated_rows(self):
        text = 'bank,category,amount\n' + 'ICBC,CURRENT,0\n' * 20
        with CaptureQueriesContext(connection) as queries:
            result = import_fund_csv(self.upload(text), actor=self.user)
        self.assertEqual(result.success_count, 20)
        profiles = [q for q in queries if 'accounts_userprofile' in q['sql']]
        self.assertLessEqual(len(profiles), 5)

    def test_partial_save_does_not_derive_from_unsaved_deposit_period(self):
        record = FundRecord.objects.create(
            user=self.user,
            bank='ICBC',
            category='CURRENT',
            amount=20,
            deposit_period=1,
        )
        record.deposit_period = 3
        record.due_date = date(2029, 11, 21)
        record.save(update_fields=['due_date'])
        record.refresh_from_db()
        self.assertEqual(record.deposit_period, 1)
        self.assertIsNone(record.start_date)
