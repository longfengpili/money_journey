from django.test import Client, TestCase
from datetime import date
from unittest.mock import patch
from django.utils import timezone

from savings_calculator import test_views
from savings_calculator.forms import AgeRangeForm, BasicParametersForm


class CalculatorApiTests(TestCase):
    setUp = test_views.CalculationViewTests.setUp

    def test_admin_login_clears_guest_planning_results(self):
        self.member.is_staff = True
        self.member.set_password("test-password")
        self.member.save()
        session = self.client.session
        session["frontend_calculation"] = {"results": [{"total": "1.00"}]}
        session["calculation_results"] = [{"total": 1}]
        session.save()
        self.client.post(
            "/admin/login/",
            {
                "username": self.member.username,
                "password": "test-password",
            },
        )
        self.assertNotIn("frontend_calculation", self.client.session)
        self.assertNotIn("calculation_results", self.client.session)

    def test_guest_write_requires_csrf_and_missing_result_is_empty(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(
            client.post(
                "/api/v1/calculator/calculate/",
                "{}",
                content_type="application/json",
            ).status_code,
            403,
        )
        self.assertEqual(
            client.get("/api/v1/calculator/result/").json()["results"], []
        )

    def test_guest_calculation_is_exact_and_restores_own_session(self):
        import json

        basic = {
            key: value
            for key, value in self.data.items()
            if not key.startswith("form-")
        }
        payload = {
            "basic": basic,
            "age_ranges": [
                {
                    "start_age": 25,
                    "end_age": 65,
                    "monthly_income": "10000",
                    "monthly_expense": "5000",
                }
            ],
        }
        response = self.client.post(
            "/api/v1/calculator/calculate/",
            json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["summary"]["final_total"], "217840.00"
        )
        self.assertEqual(len(response.json()["results"]), 40)
        self.assertEqual(
            self.client.get("/api/v1/calculator/result/").json(),
            response.json(),
        )
        self.assertNotIn("calculation_results", self.client.session)

    def test_reversed_age_range_is_reported_by_shared_form(self):
        form = AgeRangeForm(
            {
                "start_age": 40,
                "end_age": 20,
                "monthly_income": 1,
                "monthly_expense": 0,
            }
        )
        self.assertFalse(form.is_valid())

    def test_birth_year_limit_is_current_business_year(self):
        with patch(
            "savings_calculator.forms.timezone.localdate",
            return_value=date(2028, 1, 1),
        ):
            form = BasicParametersForm(
                {**self.data, "child_birth_year": "2028"}
            )
            self.assertTrue(form.is_valid(), form.errors)

    def test_age_limit_returns_clear_error_without_saving_empty_results(self):
        import json

        basic = {
            key: value
            for key, value in self.data.items()
            if not key.startswith("form-")
        }
        response = self.client.post(
            "/api/v1/calculator/calculate/",
            json.dumps(
                {
                    "basic": basic,
                    "age_ranges": [
                        {
                            "start_age": 80,
                            "end_age": 90,
                            "monthly_income": 1,
                            "monthly_expense": 0,
                        }
                    ],
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("frontend_calculation", self.client.session)
