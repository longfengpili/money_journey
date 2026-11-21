import json
import os
import subprocess
import sys
from copy import deepcopy
from datetime import date
from decimal import Decimal
from pathlib import Path

from django.test import SimpleTestCase

from savings_calculator.calculator import SavingsCalculator


def calculation_parameters():
    return {
        'parent_birth_year': 1987,
        'child_birth_year': 2014,
        'current_amount': Decimal('20000'),
        'keep_amount': Decimal('10000'),
        'three_year_rate': Decimal('1.6'),
        'annual_expense': Decimal('1200'),
        'annual_expense_month': 12,
        'calculation_months': 40,
    }


def age_parameters():
    return [
        {
            'start_age': 25,
            'end_age': 65,
            'monthly_income': Decimal('10000'),
            'monthly_expense': Decimal('5000'),
        }
    ]


class PureSavingsEngineTests(SimpleTestCase):
    def calculator(self, **kwargs):
        return SavingsCalculator(
            calculation_parameters(),
            age_parameters(),
            start_date=date(2012, 1, 1),
            initial_current_amount=Decimal('20000'),
            **kwargs,
        )

    def test_first_calculation_matches_original_months_and_summary(self):
        calculator = self.calculator()
        results = calculator.calculate()
        for index, total in (
            (0, '25000'),
            (11, '78800'),
            (35, '196400'),
            (36, '201880'),
            (39, '217840'),
        ):
            self.assertEqual(results[index]['total'], Decimal(total))
        self.assertEqual(results[11]['total_expense'], Decimal('6200'))
        self.assertEqual(results[36]['regular_transfer'], Decimal('10480'))
        self.assertEqual(results[36]['regular_deposit'], Decimal('20000'))
        self.assertEqual(results[39]['month'], '2015-04')
        self.assertEqual(
            calculator.get_summary(),
            {
                'total_months': 40,
                'final_total': 217840.0,
                'final_regular_accumulated': 200000.0,
                'final_current_deposit': 12360.0,
                'total_regular_deposit': 200000.0,
                'total_income': 400000.0,
                'total_expense': 203600.0,
                'total_balance': 196400.0,
                'average_monthly_income': 10000.0,
                'average_monthly_expense': 5000.0,
            },
        )

    def test_repeated_and_partial_then_full_calculations_are_identical(self):
        calculator = self.calculator()
        first = deepcopy(calculator.calculate())
        self.assertEqual(calculator.calculate(), first)
        calculator.calculate(months=12)
        self.assertEqual(calculator.calculate(), first)
        self.assertEqual(calculator.calculate(months=0), [])
        self.assertEqual(calculator.get_summary(), {})
        self.assertEqual(calculator.calculate(), first)

    def test_caller_input_changes_do_not_change_saved_initial_state(self):
        params, ages = calculation_parameters(), age_parameters()
        deposits = [
            [
                date(2010, 1, 1),
                date(2013, 1, 21),
                Decimal('10000'),
                Decimal('10480'),
            ]
        ]
        calculator = SavingsCalculator(
            params,
            ages,
            start_date=date(2012, 1, 1),
            initial_current_amount=Decimal('20000'),
            initial_deposits=deposits,
        )
        expected = deepcopy(calculator.calculate())
        params['keep_amount'] = Decimal('999999')
        ages[0]['monthly_income'] = Decimal('0')
        deposits[0][2] = Decimal('999999')
        deposits.append(deposits[0])
        self.assertEqual(calculator.calculate(), expected)

    def test_initial_deposit_matures_in_first_month_only_once(self):
        calculator = self.calculator(
            initial_deposits=[
                (
                    date(2009, 1, 1),
                    date(2012, 1, 21),
                    Decimal('10000'),
                    Decimal('10480'),
                ),
            ]
        )
        results = calculator.calculate(months=2)
        self.assertEqual(results[0]['regular_transfer'], Decimal('10480'))
        self.assertEqual(results[0]['total'], Decimal('35480'))
        self.assertEqual(results[1]['regular_transfer'], 0)
        self.assertEqual(calculator.calculate(months=2), results)

    def test_overlap_and_age_eighty_boundary(self):
        params = calculation_parameters()
        params['parent_birth_year'] = 1933
        calculator = SavingsCalculator(
            params,
            age_parameters()
            + [
                {
                    'start_age': 25,
                    'end_age': 150,
                    'monthly_income': Decimal('1'),
                    'monthly_expense': Decimal('1'),
                }
            ],
            start_date=date(2012, 12, 1),
            initial_current_amount=Decimal('0'),
        )
        self.assertEqual(len(calculator.calculate()), 1)
        self.assertEqual(calculator.results[0]['age'], 79)
        overlap = self.calculator()
        overlap.age_range_params.append(
            {
                'start_age': 25,
                'end_age': 150,
                'monthly_income': Decimal('1'),
                'monthly_expense': Decimal('1'),
            }
        )
        self.assertEqual(
            overlap.calculate()[0]['monthly_income'], Decimal('10000')
        )

    def test_empty_age_ranges_and_missing_initial_start_are_explicit_errors(
        self,
    ):
        with self.assertRaisesRegex(ValueError, '年龄段'):
            SavingsCalculator(
                calculation_parameters(),
                [],
                start_date=date(2012, 1, 1),
                initial_current_amount=Decimal('0'),
            )
        calculator = self.calculator(
            initial_deposits=[
                (None, date(2013, 1, 1), Decimal('10000'), Decimal('10480')),
            ]
        )
        with self.assertRaisesRegex(ValueError, '开始日期'):
            calculator.calculate()
        expired = self.calculator(
            initial_deposits=[
                (None, date(2011, 1, 1), Decimal('10000'), Decimal('10480')),
            ]
        )
        self.assertEqual(expired.calculate(), self.calculator().calculate())

    def test_import_and_calculation_work_without_django_configuration(self):
        script = '''
import json
import sys
from datetime import date
from decimal import Decimal as D
from savings_calculator.calculator import SavingsCalculator
params = dict(
    parent_birth_year=1987, child_birth_year=2014, current_amount=D('0'),
    keep_amount=D('10000'), three_year_rate=D('1.6'), annual_expense=D('0'),
    annual_expense_month=12, calculation_months=1,
)
ages = [dict(
    start_age=25, end_age=65,
    monthly_income=D('10000'), monthly_expense=D('0'),
)]
calculator = SavingsCalculator(
    params, ages, start_date=date(2012, 1, 1), initial_current_amount=D('0'),
)
result = {
    'total': str(calculator.calculate()[0]['total']),
    'django_loaded': 'django' in sys.modules,
}
print(json.dumps(result))
'''
        environment = dict(os.environ)
        environment.pop('DJANGO_SETTINGS_MODULE', None)
        result = subprocess.run(
            [sys.executable, '-c', script],
            env=environment,
            cwd=Path(__file__).resolve().parents[3],
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout),
            {
                'total': '10000',
                'django_loaded': False,
            },
        )
