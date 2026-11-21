from django.test import Client, TestCase
from django.utils import timezone

from savings_calculator import test_views
from savings_calculator.forms import AgeRangeForm, BasicParametersForm


class CalculatorApiTests(TestCase):
    setUp = test_views.CalculationViewTests.setUp

    def test_guest_write_requires_csrf_and_missing_result_is_empty(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post('/api/v1/calculator/calculate/', '{}',
                                     content_type='application/json').status_code,
                         403)
        self.assertEqual(client.get('/api/v1/calculator/result/')
                         .json()['results'], [])

    def test_guest_calculation_is_exact_and_restores_own_session(self):
        import json
        basic = {key: value for key, value in self.data.items()
                 if not key.startswith('form-')}
        payload = {'basic': basic, 'age_ranges': [{
            'start_age': 25, 'end_age': 65,
            'monthly_income': '10000', 'monthly_expense': '5000',
        }]}
        response = self.client.post('/api/v1/calculator/calculate/',
                                    json.dumps(payload),
                                    content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['summary']['final_total'], '217840.00')
        self.assertEqual(len(response.json()['results']), 40)
        self.assertEqual(self.client.get('/api/v1/calculator/result/').json(),
                         response.json())
        self.assertNotIn('calculation_results', self.client.session)

    def test_reversed_age_range_is_reported_by_shared_form(self):
        form = AgeRangeForm({'start_age': 40, 'end_age': 20,
                             'monthly_income': 1, 'monthly_expense': 0})
        self.assertFalse(form.is_valid())

    def test_birth_year_limit_is_current_business_year(self):
        self.assertEqual(BasicParametersForm().fields['child_birth_year'].max_value,
                         timezone.localdate().year)
