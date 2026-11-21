from decimal import Decimal

from django.test import SimpleTestCase

from savings_calculator.calculator import SavingsCalculator


class SavingsCalculatorAgeRangeTests(SimpleTestCase):
    def setUp(self):
        self.calculator = SavingsCalculator.__new__(SavingsCalculator)
        self.calculator.age_range_params = [
            {
                'start_age': 25,
                'end_age': 35,
                'monthly_income': Decimal('10000'),
                'monthly_expense': Decimal('5000'),
            },
            {
                'start_age': 40,
                'end_age': 50,
                'monthly_income': Decimal('8000'),
                'monthly_expense': Decimal('6000'),
            },
        ]

    def test_age_before_first_range_uses_nearest_expense_without_income(self):
        self.assertEqual(
            self.calculator._get_income_expense_by_age(24),
            (Decimal('0'), Decimal('5000')),
        )

    def test_age_inside_range_uses_income_and_expense(self):
        self.assertEqual(
            self.calculator._get_income_expense_by_age(30),
            (Decimal('10000'), Decimal('5000')),
        )

    def test_age_after_last_range_uses_nearest_expense_without_income(self):
        self.assertEqual(
            self.calculator._get_income_expense_by_age(51),
            (Decimal('0'), Decimal('6000')),
        )
