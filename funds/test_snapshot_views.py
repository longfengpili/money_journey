from datetime import date, datetime, timedelta, timezone as datetime_timezone
from importlib import import_module
from io import StringIO
from types import SimpleNamespace

from django.contrib.auth.models import Permission, User
from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile
from analytics.tasks import clean_old_records
from funds.models import FundRecord, FundSnapshot


class SnapshotViewTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user('manager')
        self.member = User.objects.create_user('member')
        UserProfile.objects.create(
            user=self.manager, is_approved=True, is_family_admin=True
        )
        UserProfile.objects.create(user=self.member, is_approved=True)
        self.asset = FundRecord.objects.create(
            user=self.member,
            bank='ICBC',
            category='CURRENT',
            amount=100,
        )

    def test_member_cannot_see_refresh_button_or_post(self):
        self.client.force_login(self.member)
        self.assertNotContains(
            self.client.get(reverse('funds:record_list')),
            'action="' + reverse('funds:create_snapshot') + '"',
        )
        response = self.client.post(reverse('funds:create_snapshot'))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(FundSnapshot.objects.count(), 0)

    def test_manager_can_refresh_same_day(self):
        self.client.force_login(self.manager)
        self.assertContains(
            self.client.get(reverse('funds:record_list')), '刷新当天快照'
        )
        response = self.client.post(
            reverse('funds:create_snapshot'), follow=True
        )
        self.assertContains(response, '已刷新')
        before = FundSnapshot.objects.get(user=self.member)
        self.asset.amount = 150
        self.asset.save()
        self.client.post(reverse('funds:create_snapshot'))
        after = FundSnapshot.objects.get(user=self.member)
        self.assertEqual(after.pk, before.pk)
        self.assertEqual(after.total_amount, 150)
        self.assertEqual(FundSnapshot.objects.count(), 2)

    def test_admin_shows_computed_snapshot_and_blocks_manual_changes(self):
        self.client.force_login(self.manager)
        self.client.post(reverse('funds:create_snapshot'))
        snapshot = FundSnapshot.objects.get(user=self.member)
        self.member.is_staff = True
        self.member.save()
        self.member.user_permissions.set(
            Permission.objects.filter(content_type__app_label='funds')
        )
        self.client.force_login(self.member)
        url = reverse('admin:funds_fundsnapshot_change', args=[snapshot.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(
            self.client.post(url, {'total_amount': '999'}).status_code, 403
        )
        self.client.post(
            reverse('admin:funds_fundsnapshot_changelist'),
            {
                'action': 'delete_selected',
                '_selected_action': [snapshot.pk],
                'post': 'yes',
            },
        )
        snapshot.refresh_from_db()
        self.assertEqual(snapshot.total_amount, 100)
        self.assertEqual(
            self.client.get(
                reverse('admin:funds_fundsnapshot_add')
            ).status_code,
            403,
        )


class HistoricalRecordCheckTests(TestCase):
    def test_old_record_check_only_reports_finished_candidates(self):
        now = datetime(2026, 11, 21, tzinfo=datetime_timezone.utc)
        for status, days in (
            ('ACTIVE', 1500),
            ('WITHDRAWN', 1500),
            ('ROLLED_OVER', 1500),
            ('WITHDRAWN', 10),
        ):
            record = FundRecord.objects.create(
                bank='ICBC',
                category='CURRENT',
                amount=100,
                savings_status=status,
            )
            FundRecord.objects.filter(pk=record.pk).update(
                created_at=now - timedelta(days=1600),
                updated_at=now - timedelta(days=days),
            )
        before = list(FundRecord.objects.order_by('pk').values())
        self.assertEqual(clean_old_records(now=now), 2)
        self.assertEqual(
            list(FundRecord.objects.order_by('pk').values()), before
        )


class SnapshotMigrationCheckTests(TransactionTestCase):
    def test_old_duplicate_rows_are_reported_without_modification(self):
        old_target = [('funds', '0013_fundrecord_created_by')]
        new_target = [('funds', '0014_daily_snapshot_refresh')]
        executor = MigrationExecutor(connection)
        executor.migrate(old_target)
        old_apps = executor.loader.project_state(old_target).apps
        old_snapshot = old_apps.get_model('funds', 'FundSnapshot')
        manager = User.objects.create_user('migration_manager')
        try:
            for _ in range(2):
                old_snapshot.objects.create(
                    user_id=manager.pk,
                    created_by_id=manager.pk,
                    snapshot_date=date(2026, 11, 21),
                    total_amount=100,
                    record_count=1,
                )
            output = StringIO()
            call_command('audit_snapshots', stdout=output)
            self.assertIn('重复用户日', output.getvalue())
            migration = import_module(
                'funds.migrations.0014_daily_snapshot_refresh'
            )
            with self.assertRaisesRegex(RuntimeError, 'audit_snapshots'):
                migration.check_duplicate_user_days(
                    old_apps,
                    SimpleNamespace(connection=connection),
                )
            self.assertEqual(old_snapshot.objects.count(), 2)
        finally:
            # 清理隔离测试数据库中的迁移样例，恢复测试所需的新结构。
            User.objects.filter(pk=manager.pk).delete()
            MigrationExecutor(connection).migrate(new_target)
