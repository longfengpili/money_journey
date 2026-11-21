"""组件化总览与图表 API 的集成回归。"""

from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import UserProfile
from funds.models import FundRecord, FundSnapshot


class AnalyticsPageTests(TestCase):
    def setUp(self):
        self.member = User.objects.create_user("before", first_name="成员")
        UserProfile.objects.create(user=self.member, is_approved=True)
        self.other = User.objects.create_user("other")
        for user, bank, category, amount, status in (
            (self.member, "ICBC", "CURRENT", "12.34", "ACTIVE"),
            (self.other, "CCB", "SAVINGS", "0.01", "ACTIVE"),
            (self.member, "ICBC", "CURRENT", "999", "WITHDRAWN"),
        ):
            FundRecord.objects.create(
                user=user,
                bank=bank,
                category=category,
                amount=amount,
                savings_status=status,
            )
        self.client.force_login(self.member)

    def summary(self, **filters):
        response = self.client.get("/api/v1/analytics/summary/", filters)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        return response.json()

    def trend(self, **filters):
        response = self.client.get("/api/v1/analytics/trend/", filters)
        self.assertEqual(response.status_code, 200)
        return response.json()["results"]

    def test_all_dimensions_use_same_active_totals(self):
        payload = self.summary()
        self.assertEqual(payload["total_amount"], "12.35")
        for dimension in ("owner", "bank", "category"):
            rows = payload[dimension + "_summary"]
            self.assertEqual(
                [row["total_amount"] for row in rows], ["12.34", "0.01"]
            )
            self.assertEqual(
                sum(Decimal(row["total_amount"]) for row in rows),
                Decimal(payload["total_amount"]),
            )

    def test_special_names_round_trip_as_json_data(self):
        name = '家人\'"\n</script><script>alert("name")</script>&'
        self.member.first_name = name
        self.member.save()
        self.assertEqual(
            self.summary()["owner_summary"][0]["first_name"], name
        )

    def test_renamed_owner_trend_uses_account_and_preserves_history(self):
        snapshot = FundSnapshot.objects.create(
            user=self.member,
            owner="before",
            created_by=self.other,
            snapshot_date=date(2026, 11, 20),
            total_amount="7.89",
            record_count=1,
            bank_summary={"ICBC": 7.89},
        )
        self.member.username = "after"
        self.member.save()
        filters = {
            "owner": "after",
            "bank": "CCB",
            "savings_status": "WITHDRAWN",
        }
        self.assertEqual(self.summary(**filters)["total_amount"], "0.00")
        rows = self.trend(**filters)
        self.assertEqual(rows[0]["snapshot_date"], "2026-11-20")
        self.assertEqual(rows[0]["total_amount"], "7.89")
        snapshot.refresh_from_db()
        self.assertEqual(snapshot.owner, "before")
        self.assertEqual(snapshot.bank_summary, {"ICBC": 7.89})

    def test_explicit_all_status_affects_live_stats(self):
        payload = self.summary(owner="before", savings_status="")
        self.assertEqual(payload["total_amount"], "1011.34")
        self.assertEqual(payload["total_records"], 2)
        self.assertEqual(payload["filters"]["savings_status"], "")

    def test_partial_and_history_only_owner_filters_remain_available(self):
        for user, name, amount in (
            (self.other, "old_other", 10),
            (self.member, "before", 1),
        ):
            FundSnapshot.objects.create(
                user=user,
                owner=name,
                created_by=self.member,
                snapshot_date=date(2026, 11, 20),
                total_amount=amount,
                record_count=1,
            )
        FundRecord.objects.filter(user=self.other).update(user=self.member)
        for owner, amount in (("bef", "1.00"), ("other", "10.00")):
            self.assertEqual(
                self.summary(owner=owner)["filters"]["owner"], owner
            )
            self.assertEqual(
                self.trend(owner=owner)[0]["total_amount"], amount
            )
        self.assertEqual(self.summary(owner="other")["total_amount"], "0.00")
        FundRecord.objects.create(
            owner="before", bank="ICBC", category="CURRENT", amount=0
        )
        self.assertEqual(len(self.summary(owner="before")["owner_summary"]), 2)
        self.assertEqual(len(self.trend(owner="before")), 1)

    def test_empty_filter_result_and_absent_snapshots_are_usable(self):
        payload = self.summary(owner="missing")
        self.assertEqual(payload["total_amount"], "0.00")
        self.assertEqual(payload["bank_summary"], [])
        self.assertEqual(self.trend(owner="missing"), [])

    def test_guest_demo_uses_json_and_ignores_real_assets(self):
        self.client.logout()
        payload = self.summary(owner="before", bank="ICBC")
        self.assertEqual(payload["total_amount"], "1280000.00")
        self.assertEqual(
            [row["total_amount"] for row in payload["category_summary"]],
            ["680000.00", "320000.00", "180000.00", "100000.00"],
        )
        self.assertEqual(self.trend(owner="before"), [])
        self.assertEqual(payload["filters"]["owner"], "")
        self.assertEqual(self.client.get("/api/v1/funds/").status_code, 403)
