from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser, User
from django.test import TestCase

from funds.models import FundRecord
from savings_calculator.inputs import prepare_calculation_inputs
from savings_calculator.test_engine import (
    age_parameters,
    calculation_parameters,
)


class CalculationInputTests(TestCase):
    def test_guest_uses_form_cash_and_age_start_without_database_or_clock(
        self,
    ):
        with self.assertNumQueries(0), patch(
            'savings_calculator.inputs.timezone.localdate',
            side_effect=AssertionError('游客不需要系统日期'),
        ):
            inputs = prepare_calculation_inputs(
                calculation_parameters(),
                age_parameters(),
                user=AnonymousUser(),
            )
        self.assertEqual(
            inputs,
            {
                'start_date': date(2012, 1, 1),
                'initial_current_amount': Decimal('20000'),
                'initial_deposits': [],
            },
        )

    def test_authenticated_family_assets_keep_original_grouping_in_one_query(
        self,
    ):
        member = User.objects.create_user('member')
        other = User.objects.create_user('other')
        for user, amount in ((member, 100), (other, 200)):
            FundRecord.objects.create(
                user=user,
                bank='ICBC',
                category='CURRENT',
                amount=amount,
            )
        FundRecord.objects.create(
            user=other,
            bank='ICBC',
            category='CURRENT',
            amount=999,
            savings_status='WITHDRAWN',
        )
        for category, amount, rate in (
            ('FUND', 1000, Decimal('2.25')),
            ('SAVINGS', 2000, Decimal('1.50')),
            ('SAVINGS', 500, None),
        ):
            FundRecord.objects.create(
                user=other,
                bank='ICBC',
                category=category,
                amount=amount,
                interest_rate=rate,
                deposit_period=3,
                start_date=date(2023, 11, 21),
                due_date=date(2026, 11, 21),
            )
        FundRecord.objects.create(
            user=other,
            bank='ICBC',
            category='SAVINGS',
            amount=70,
            due_date=date(2027, 1, 1),
        )
        with self.assertNumQueries(1):
            inputs = prepare_calculation_inputs(
                calculation_parameters(),
                age_parameters(),
                user=member,
                today=date(2026, 11, 21),
            )
        self.assertEqual(inputs['start_date'], date(2026, 11, 1))
        self.assertEqual(inputs['initial_current_amount'], Decimal('300'))
        self.assertEqual(
            inputs['initial_deposits'],
            [
                (
                    date(2023, 11, 21),
                    date(2026, 11, 21),
                    Decimal('3500'),
                    Decimal('3157.5'),
                ),
            ],
        )

    def test_default_start_date_uses_django_localdate(self):
        member = User.objects.create_user('member')
        with patch(
            'savings_calculator.inputs.timezone.localdate',
            return_value=date(2026, 12, 31),
        ):
            inputs = prepare_calculation_inputs(
                calculation_parameters(),
                age_parameters(),
                user=member,
            )
        self.assertEqual(inputs['start_date'], date(2026, 12, 1))
        self.assertEqual(inputs['initial_current_amount'], Decimal('0'))
        self.assertEqual(inputs['initial_deposits'], [])
