from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from accounts.models import UserProfile
from funds.models import FundRecord, FundSnapshot


class AnalyticsApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("member")
        UserProfile.objects.create(user=self.user, is_approved=True)
        self.other = User.objects.create_user("other")
        for user, amount in ((self.user, "12.34"), (self.other, "5.67")):
            FundRecord.objects.create(
                user=user, bank="ICBC", category="CURRENT", amount=amount
            )

    def test_guest_only_gets_demo_and_member_gets_decimal_strings(self):
        response = self.client.get("/api/v1/analytics/summary/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["demo"])
        self.assertEqual(
            sum(
                Decimal(row["total_amount"])
                for row in response.json()["owner_category_summary"]
            ),
            Decimal(response.json()["total_amount"]),
        )
        self.client.force_login(self.user)
        data = self.client.get("/api/v1/analytics/summary/").json()
        self.assertEqual(data["total_amount"], "18.01")
        self.assertEqual(data["total_records"], 2)
        filtered = self.client.get(
            "/api/v1/analytics/summary/",
            {
                "owner_id": self.user.pk,
            },
        ).json()
        self.assertEqual(filtered["total_amount"], "12.34")

    def test_maturity_chart_respects_active_assets_and_filters(self):
        next_month = (timezone.localdate().replace(day=1) + timedelta(days=32))
        next_month = next_month.replace(day=1)
        FundRecord.objects.create(
            user=self.user, bank="ICBC", category="SAVINGS",
            amount="30.25", due_date=next_month,
        )
        FundRecord.objects.create(
            user=self.other, bank="CCB", category="SAVINGS",
            amount="99.00", due_date=next_month,
            savings_status="WITHDRAWN",
        )
        self.client.force_login(self.user)
        rows = self.client.get("/api/v1/analytics/summary/").json()[
            "maturity_summary"
        ]
        self.assertEqual(len(rows), 6)
        self.assertEqual(rows[1], {
            "month": next_month.strftime("%Y-%m"),
            "total_amount": "30.25", "record_count": 1,
        })
        filtered = self.client.get(
            "/api/v1/analytics/summary/", {"bank": "CCB"}
        ).json()["maturity_summary"]
        self.assertTrue(all(row["total_amount"] == "0.00" for row in filtered))

    def test_owner_id_selects_renamed_history_and_revoked_access_is_denied(
        self,
    ):
        FundSnapshot.objects.create(
            user=self.user,
            owner="old",
            created_by=self.other,
            snapshot_date=date(2026, 11, 20),
            total_amount="12.34",
            record_count=1,
        )
        self.client.force_login(self.user)
        data = self.client.get(
            "/api/v1/analytics/trend/",
            {
                "owner_id": self.user.pk,
            },
        ).json()
        self.assertEqual(data["results"][0]["total_amount"], "12.34")
        self.user.userprofile.is_approved = False
        self.user.userprofile.save()
        self.assertEqual(
            self.client.get("/api/v1/analytics/summary/").status_code, 403
        )
