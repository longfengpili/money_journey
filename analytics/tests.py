from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import UserProfile
from funds.models import FundRecord


class FamilyAnalyticsTests(TestCase):
    def test_shared_totals_follow_account_after_rename(self):
        viewer = User.objects.create_user("viewer")
        UserProfile.objects.create(user=viewer, is_approved=True)
        owner = User.objects.create_user("old", first_name="母亲")
        first = FundRecord.objects.create(
            user=owner,
            bank="ICBC",
            category="CURRENT",
            amount=100,
        )
        owner.username = "new"
        owner.save()
        FundRecord.objects.create(
            user=owner,
            bank="ICBC",
            category="CURRENT",
            amount=200,
        )
        FundRecord.objects.create(
            owner="legacy",
            bank="ICBC",
            category="CURRENT",
            amount=50,
        )
        self.client.force_login(viewer)
        response = self.client.get("/api/v1/analytics/summary/")
        self.assertEqual(response.json()["total_amount"], "350.00")
        self.assertEqual(response.json()["owner_count"], 2)
        summary = response.json()["owner_summary"][0]
        self.assertEqual(summary["owner"], "new")
        self.assertEqual(summary["first_name"], "母亲")
        self.assertEqual(summary["total_amount"], "300.00")
        filtered = self.client.get(
            "/api/v1/analytics/summary/", {"owner": "new"}
        )
        self.assertEqual(filtered.json()["total_amount"], "300.00")
        records = self.client.get("/api/v1/funds/").json()["results"]
        self.assertEqual(records[0]["owner_display"], "母亲")
        first.refresh_from_db()
        self.assertEqual(first.owner, "old")
