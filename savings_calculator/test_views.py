from datetime import date
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from funds.models import FundRecord


class CalculationViewTests(TestCase):
    def setUp(self):
        self.data = {
            'parent_birth_year': '1987',
            'child_birth_year': '2014',
            'current_amount': '20000',
            'keep_amount': '10000',
            'three_year_rate': '1.6',
            'annual_expense': '1200',
            'annual_expense_month': '12',
            'calculation_months': '40',
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '0',
            'form-MIN_NUM_FORMS': '1',
            'form-MAX_NUM_FORMS': '20',
            'form-0-start_age': '25',
            'form-0-end_age': '65',
            'form-0-monthly_income': '10000',
            'form-0-monthly_expense': '5000',
        }
        self.member = User.objects.create_user('member')
        UserProfile.objects.create(user=self.member, is_approved=True)

    def test_guest_results_and_repeated_requests_keep_session_contract(self):
        url = reverse('savings_calculator:calculate')
        self.assertEqual(self.client.post(url, self.data).status_code, 302)
        expected = dict(self.client.session)
        self.assertEqual(
            expected['calculation_results'][0]['month'], '2012-01'
        )
        self.assertEqual(
            expected['calculation_summary']['final_total'], 217840
        )
        self.assertEqual(self.client.post(url, self.data).status_code, 302)
        self.assertEqual(dict(self.client.session), expected)
        self.assertEqual(
            self.client.get(
                reverse('savings_calculator:results'),
            ).status_code,
            200,
        )

    def test_logged_in_member_uses_all_family_assets_and_local_month(self):
        self.client.force_login(self.member)
        other = User.objects.create_user('other')
        for user, amount in ((self.member, 500), (other, 1500)):
            FundRecord.objects.create(
                user=user,
                bank='ICBC',
                category='CURRENT',
                amount=amount,
            )
        FundRecord.objects.create(
            user=other,
            bank='ICBC',
            category='SAVINGS',
            amount=10000,
            interest_rate='1.60',
            deposit_period=3,
            start_date=date(2023, 11, 21),
            due_date=date(2026, 11, 21),
        )
        with patch(
            'savings_calculator.inputs.timezone.localdate',
            return_value=date(2026, 11, 21),
        ):
            self.assertEqual(
                self.client.post(
                    reverse('savings_calculator:calculate'),
                    self.data,
                ).status_code,
                302,
            )
        rows = self.client.session['calculation_results']
        self.assertEqual(rows[0]['month'], '2026-11')
        self.assertEqual(rows[0]['current_deposit_before_expense'], 2000)
        self.assertEqual(rows[0]['regular_transfer'], 10480)
        self.assertEqual(rows[0]['total'], 17480)
        self.assertEqual(rows[1]['regular_transfer'], 0)
        self.assertEqual(rows[1]['total_expense'], 6200)

    def test_missing_or_empty_results_redirect_to_input(self):
        for results in (None, []):
            if results is not None:
                session = self.client.session
                session['calculation_results'] = results
                session.save()
            response = self.client.get(reverse('savings_calculator:results'))
            self.assertRedirects(
                response,
                reverse('savings_calculator:calculator_input'),
            )

    def test_age_eighty_empty_calculation_returns_to_input(self):
        self.client.force_login(self.member)
        response = self.client.post(
            reverse('savings_calculator:calculate'),
            {**self.data, 'parent_birth_year': '1900'},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.request['PATH_INFO'],
            reverse(
                'savings_calculator:calculator_input',
            ),
        )
        self.assertContains(response, '没有找到计算结果')

    def test_legacy_missing_start_date_has_clear_error(self):
        self.client.force_login(self.member)
        record = FundRecord.objects.create(
            user=self.member,
            bank='ICBC',
            category='SAVINGS',
            amount=10000,
            interest_rate='1.60',
            deposit_period=3,
            due_date=date(2090, 1, 1),
        )
        FundRecord.objects.filter(pk=record.pk).update(start_date=None)
        response = self.client.post(
            reverse('savings_calculator:calculate'),
            self.data,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '开始日期')

    def test_deleted_age_range_is_not_used_for_calculation(self):
        data = {
            **self.data,
            'form-TOTAL_FORMS': '2',
            'form-0-DELETE': 'on',
            'form-1-start_age': '25',
            'form-1-end_age': '65',
            'form-1-monthly_income': '7000',
            'form-1-monthly_expense': '5000',
        }
        response = self.client.post(
            reverse('savings_calculator:calculate'),
            data,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            self.client.session['calculation_results'][0]['monthly_income'],
            7000,
        )
