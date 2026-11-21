from datetime import date
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
import json

from savings_calculator.forms import create_age_range_formset

from accounts.models import UserProfile
from funds.models import FundRecord


class CalculationViewTests(TestCase):
    def setUp(self):
        self.data = {
            "parent_birth_year": "1987",
            "child_birth_year": "2014",
            "current_amount": "20000",
            "keep_amount": "10000",
            "three_year_rate": "1.6",
            "annual_expense": "1200",
            "annual_expense_month": "12",
            "calculation_months": "40",
            "form-TOTAL_FORMS": "1",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "1",
            "form-MAX_NUM_FORMS": "20",
            "form-0-start_age": "25",
            "form-0-end_age": "65",
            "form-0-monthly_income": "10000",
            "form-0-monthly_expense": "5000",
        }
        self.member = User.objects.create_user("member")
        UserProfile.objects.create(user=self.member, is_approved=True)

    def calculate(self, data=None):
        data = self.data if data is None else data
        # 删除的年龄段在前端提交前排除；继续检验共享表单的删除语义。
        formset = create_age_range_formset()(data)
        self.assertTrue(formset.is_valid(), formset.errors)
        payload = {
            "basic": {
                key: value
                for key, value in data.items()
                if not key.startswith("form-")
            },
            "age_ranges": [
                {
                    key: str(value)
                    for key, value in form.cleaned_data.items()
                    if key != "DELETE"
                }
                for form in formset
                if form.cleaned_data and not form.cleaned_data.get("DELETE")
            ],
        }
        return self.client.post(
            "/api/v1/calculator/calculate/",
            json.dumps(payload),
            content_type="application/json",
        )

    def test_guest_results_and_repeated_requests_keep_session_contract(self):
        response = self.calculate()
        self.assertEqual(response.status_code, 200)
        expected = response.json()
        self.assertEqual(expected["results"][0]["month"], "2012-01")
        self.assertEqual(expected["summary"]["final_total"], "217840.00")
        self.assertEqual(self.calculate().json(), expected)
        self.assertEqual(
            self.client.get("/api/v1/calculator/result/").json(), expected
        )

    def test_logged_in_member_uses_all_family_assets_and_local_month(self):
        self.client.force_login(self.member)
        other = User.objects.create_user("other")
        for user, amount in ((self.member, 500), (other, 1500)):
            FundRecord.objects.create(
                user=user, bank="ICBC", category="CURRENT", amount=amount
            )
        FundRecord.objects.create(
            user=other,
            bank="ICBC",
            category="SAVINGS",
            amount=10000,
            interest_rate="1.60",
            deposit_period=3,
            start_date=date(2023, 11, 21),
            due_date=date(2026, 11, 21),
        )
        with patch(
            "savings_calculator.inputs.timezone.localdate",
            return_value=date(2026, 11, 21),
        ):
            response = self.calculate()
        self.assertEqual(response.status_code, 200)
        rows = response.json()["results"]
        self.assertEqual(rows[0]["month"], "2026-11")
        self.assertEqual(rows[0]["current_deposit_before_expense"], "2000.00")
        self.assertEqual(rows[0]["regular_transfer"], "10480.00")
        self.assertEqual(rows[0]["total"], "17480.00")
        self.assertEqual(rows[1]["regular_transfer"], "0.00")
        self.assertEqual(rows[1]["total_expense"], "6200.00")

    def test_missing_results_restore_empty_planning(self):
        payload = self.client.get("/api/v1/calculator/result/").json()
        self.assertEqual(payload["results"], [])
        self.assertIsNone(payload["params"])

    def test_age_eighty_empty_calculation_returns_clear_error(self):
        self.client.force_login(self.member)
        response = self.calculate({**self.data, "parent_birth_year": "1900"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("__all__", response.json()["fields"])
        self.assertNotIn("frontend_calculation", self.client.session)

    def test_legacy_missing_start_date_has_clear_error(self):
        self.client.force_login(self.member)
        record = FundRecord.objects.create(
            user=self.member,
            bank="ICBC",
            category="SAVINGS",
            amount=10000,
            interest_rate="1.60",
            deposit_period=3,
            due_date=date(2090, 1, 1),
        )
        FundRecord.objects.filter(pk=record.pk).update(start_date=None)
        response = self.calculate()
        self.assertEqual(response.status_code, 400)
        self.assertIn("开始日期", str(response.json()["fields"]))

    def test_deleted_age_range_is_not_used_for_calculation(self):
        response = self.calculate(
            {
                **self.data,
                "form-TOTAL_FORMS": "2",
                "form-0-DELETE": "on",
                "form-1-start_age": "25",
                "form-1-end_age": "65",
                "form-1-monthly_income": "7000",
                "form-1-monthly_expense": "5000",
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["results"][0]["monthly_income"], "7000.00"
        )
