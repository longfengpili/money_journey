import io
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone as datetime_timezone
from decimal import Decimal
from threading import Barrier
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser, User
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.db import (
    DatabaseError,
    IntegrityError,
    close_old_connections,
    transaction,
)
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature
from django.utils import timezone

from accounts.models import UserProfile
from funds.models import FundRecord, FundSnapshot
from funds.snapshots import refresh_daily_snapshots


class DailySnapshotTests(TestCase):
    def setUp(self):
        self.day = date(2026, 11, 21)
        self.manager = User.objects.create_user("manager")
        self.member = User.objects.create_user("member")
        self.other = User.objects.create_user("other")
        for user in (self.manager, self.member, self.other):
            UserProfile.objects.create(
                user=user,
                is_approved=True,
                is_family_admin=user == self.manager,
            )
        self.asset = FundRecord.objects.create(
            user=self.member,
            bank="ICBC",
            category="CURRENT",
            amount=Decimal("9999999999999.99"),
        )
        FundRecord.objects.create(
            user=self.member,
            bank="CCB",
            category="CURRENT",
            amount="0.01",
        )

    def refresh(self, actor=None):
        return refresh_daily_snapshots(
            actor or self.manager,
            snapshot_date=self.day,
        )

    def test_archived_member_history_remains_without_future_snapshots(self):
        day = timezone.localdate()
        refresh_daily_snapshots(self.manager, snapshot_date=day)
        old_snapshot = FundSnapshot.objects.get(
            user=self.member, snapshot_date=day
        )
        original_total = old_snapshot.total_amount
        self.member.userprofile.is_archived = True
        self.member.userprofile.save(update_fields=["is_archived"])
        FundRecord.objects.filter(user=self.member).update(
            user=self.other, owner=self.other.username
        )
        refresh_daily_snapshots(self.manager, snapshot_date=day)
        old_snapshot.refresh_from_db()
        self.assertEqual(old_snapshot.total_amount, 0)
        self.assertEqual(
            FundSnapshot.objects.get(
                user=self.other, snapshot_date=day
            ).total_amount, original_total,
        )
        next_day = day + timedelta(days=1)
        refresh_daily_snapshots(self.manager, snapshot_date=next_day)
        self.assertFalse(FundSnapshot.objects.filter(
            user=self.member, snapshot_date=next_day
        ).exists())

    def test_refresh_updates_same_rows_and_tracks_latest_asset_state(self):
        result = self.refresh()
        self.assertEqual((result.created_count, result.updated_count), (3, 0))
        snapshot = FundSnapshot.objects.get(user=self.member)
        original_ids = list(
            FundSnapshot.objects.order_by("pk").values_list("pk", flat=True)
        )
        original_created_at = snapshot.created_at
        self.assertEqual(snapshot.total_amount, Decimal("10000000000000.00"))
        self.assertEqual(
            snapshot.bank_summary, {"ICBC": "9999999999999.99", "CCB": "0.01"}
        )
        self.assertEqual(
            snapshot.category_summary, {"CURRENT": "10000000000000.00"}
        )
        self.assertEqual(
            FundSnapshot.objects.get(user=self.other).total_amount, 0
        )

        self.asset.amount = Decimal("25.25")
        self.asset.save()
        self.refresh()
        snapshot.refresh_from_db()
        self.assertEqual(snapshot.total_amount, Decimal("25.26"))
        self.asset.user = self.other
        self.asset.save()
        self.refresh()
        self.assertEqual(
            FundSnapshot.objects.get(user=self.other).total_amount,
            Decimal("25.25"),
        )
        self.assertEqual(
            FundSnapshot.objects.get(user=self.member).total_amount,
            Decimal("0.01"),
        )

        self.asset.savings_status = "WITHDRAWN"
        self.asset.save()
        FundRecord.objects.create(
            user=self.other,
            bank="CMB",
            category="FUND",
            amount="7.33",
        )
        self.other.userprofile.is_family_admin = True
        self.other.userprofile.save()
        result = self.refresh(self.other)
        self.assertEqual((result.created_count, result.updated_count), (0, 3))
        self.assertEqual(
            list(
                FundSnapshot.objects.order_by("pk").values_list(
                    "pk", flat=True
                )
            ),
            original_ids,
        )
        snapshot.refresh_from_db()
        self.assertEqual(snapshot.created_at, original_created_at)
        self.assertEqual(snapshot.created_by, self.other)
        other = FundSnapshot.objects.get(user=self.other)
        self.assertEqual(other.total_amount, Decimal("7.33"))
        self.assertEqual(other.category_summary, {"FUND": "7.33"})

    def test_old_numeric_history_survives_filling_missing_members(
        self,
    ):
        old = FundSnapshot.objects.create(
            user=self.member,
            owner="old_name",
            created_by=self.manager,
            snapshot_date=self.day - timedelta(days=1),
            total_amount=9,
            record_count=1,
            bank_summary={"ICBC": 9.0},
        )
        today = FundSnapshot.objects.create(
            user=self.member,
            created_by=self.manager,
            snapshot_date=self.day,
            total_amount=1,
            record_count=1,
        )
        result = self.refresh()
        self.assertEqual((result.created_count, result.updated_count), (2, 1))
        old.refresh_from_db()
        self.assertEqual(old.total_amount, 9)
        self.assertEqual(old.owner, "old_name")
        self.assertEqual(old.bank_summary, {"ICBC": 9.0})
        today.refresh_from_db()
        self.assertEqual(today.total_amount, Decimal("10000000000000.00"))
        self.client.force_login(self.member)
        response = self.client.get("/api/v1/analytics/trend/")
        self.assertEqual(
            [row["total_amount"] for row in response.json()["results"]],
            ["9.00", "10000000000000.00"],
        )

    def test_failure_after_updates_rolls_back_entire_family(self):
        old = FundSnapshot.objects.create(
            user=self.member,
            created_by=self.manager,
            snapshot_date=self.day,
            total_amount=9,
            record_count=1,
            bank_summary={"ICBC": 9.0},
        )

        def fail_new_rows(*args, **kwargs):
            self.assertEqual(
                FundSnapshot.objects.get(pk=old.pk).total_amount,
                Decimal("10000000000000.00"),
            )
            raise DatabaseError("测试新增行失败")

        with patch(
            "funds.snapshots.FundSnapshot.objects.bulk_create",
            side_effect=fail_new_rows,
        ):
            with self.assertRaises(DatabaseError):
                self.refresh()
        old.refresh_from_db()
        self.assertEqual(FundSnapshot.objects.count(), 1)
        self.assertEqual(old.total_amount, 9)
        self.assertEqual(old.bank_summary, {"ICBC": 9.0})

    def test_permission_checks_apply_to_direct_service_calls(self):
        for actor in (self.member, AnonymousUser()):
            with self.assertRaises(PermissionDenied):
                refresh_daily_snapshots(actor, snapshot_date=self.day)
        self.manager.is_active = False
        with self.assertRaises(PermissionDenied):
            self.refresh()
        self.assertEqual(FundSnapshot.objects.count(), 0)

    def test_unassigned_assets_and_today_legacy_snapshots_are_reported(self):
        asset = FundRecord.objects.create(
            owner="legacy",
            bank="ICBC",
            category="CURRENT",
            amount=10,
        )
        with self.assertRaisesRegex(ValidationError, "归属"):
            self.refresh()
        self.assertEqual(FundSnapshot.objects.count(), 0)
        asset.user = self.member
        asset.save()
        legacy = FundSnapshot.objects.create(
            user=None,
            owner="legacy",
            created_by=self.manager,
            snapshot_date=self.day,
            total_amount=10,
            record_count=1,
        )
        with self.assertRaisesRegex(ValidationError, "归属"):
            self.refresh()
        legacy.snapshot_date -= timedelta(days=1)
        legacy.save()
        self.refresh()
        self.assertEqual(FundSnapshot.objects.count(), 4)

    def test_local_day_and_long_username_zero_asset_member(self):
        long_user = User.objects.create_user("u" * 150)
        instant = datetime(2026, 11, 20, 16, 30, tzinfo=datetime_timezone.utc)
        with timezone.override("Asia/Shanghai"), patch(
            "django.utils.timezone.now",
            return_value=instant,
        ):
            result = refresh_daily_snapshots(self.manager)
            unsaved = FundSnapshot()
        self.assertEqual(result.snapshot_date, date(2026, 11, 21))
        self.assertEqual(unsaved.snapshot_date, date(2026, 11, 21))
        snapshot = FundSnapshot.objects.get(user=long_user)
        self.assertEqual(snapshot.owner, long_user.username)
        self.assertEqual(snapshot.total_amount, 0)

    def test_database_enforces_user_day_uniqueness(self):
        self.refresh()
        with self.assertRaises(IntegrityError), transaction.atomic():
            FundSnapshot.objects.create(
                user=self.member,
                created_by=self.manager,
                snapshot_date=self.day,
                total_amount=1,
                record_count=1,
            )

    def test_audit_command_does_not_change_records(self):
        FundSnapshot.objects.create(
            owner="legacy",
            created_by=self.manager,
            total_amount=5,
            record_count=1,
        )
        FundRecord.objects.create(
            owner="legacy", bank="ICBC", category="CURRENT", amount=5
        )
        before_assets = list(FundRecord.objects.order_by("pk").values())
        before_snapshots = list(FundSnapshot.objects.order_by("pk").values())
        output = io.StringIO()
        call_command("audit_snapshots", stdout=output)
        self.assertIn("未关联", output.getvalue())
        self.assertEqual(
            list(FundRecord.objects.order_by("pk").values()), before_assets
        )
        self.assertEqual(
            list(FundSnapshot.objects.order_by("pk").values()),
            before_snapshots,
        )


@skipUnlessDBFeature("has_select_for_update")
class ConcurrentSnapshotTests(TransactionTestCase):
    def test_two_refreshes_have_one_complete_user_day_set(self):
        manager = User.objects.create_user("manager")
        member = User.objects.create_user("member")
        UserProfile.objects.create(
            user=manager, is_approved=True, is_family_admin=True
        )
        FundRecord.objects.create(
            user=member, bank="ICBC", category="CURRENT", amount="123.45"
        )
        barrier = Barrier(2)

        def worker():
            close_old_connections()
            try:
                actor = User.objects.get(pk=manager.pk)
                barrier.wait(timeout=10)
                return refresh_daily_snapshots(
                    actor, snapshot_date=date(2026, 11, 21)
                )
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(worker) for _ in range(2)]
            results = [future.result(timeout=20) for future in futures]
        self.assertEqual(FundSnapshot.objects.count(), 2)
        self.assertEqual(sum(result.created_count for result in results), 2)
        self.assertEqual(
            FundSnapshot.objects.get(user=member).total_amount,
            Decimal("123.45"),
        )
