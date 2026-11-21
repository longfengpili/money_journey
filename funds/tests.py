import io

from django.contrib.auth.models import Permission, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.urls import reverse

from accounts.models import UserProfile
from funds.models import FundRecord


class AssetOwnershipTests(TestCase):
    def setUp(self):
        self.member = User.objects.create_user('member')
        self.other = User.objects.create_user('other', first_name='母亲')
        self.manager = User.objects.create_user('manager')
        for user in (self.member, self.other, self.manager):
            UserProfile.objects.create(user=user, is_approved=True)
        UserProfile.objects.filter(user=self.manager).update(
            is_family_admin=True
        )
        self.record = FundRecord.objects.create(
            user=self.other,
            created_by=self.member,
            bank='ICBC',
            category='CURRENT',
            amount=100,
        )
        self.data = {'bank': 'ICBC', 'category': 'CURRENT', 'amount': '200'}

    def test_member_cannot_edit_or_claim_other_assets(self):
        self.client.force_login(self.member)
        self.client.post(
            reverse('funds:edit_record', args=[self.record.pk]), self.data
        )
        self.record.refresh_from_db()
        self.assertEqual(self.record.amount, 100)
        self.client.post(
            reverse('funds:add_record'),
            {
                **self.data,
                'owner': self.other.username,
            },
        )
        self.assertEqual(FundRecord.objects.count(), 1)
        self.client.post(reverse('funds:add_record'), self.data)
        created = FundRecord.objects.latest('pk')
        self.assertEqual(created.user, self.member)
        self.assertEqual(created.created_by, self.member)

    def test_manager_edit_preserves_owner_and_creator_and_can_transfer(self):
        self.client.force_login(self.manager)
        self.client.post(
            reverse('funds:edit_record', args=[self.record.pk]), self.data
        )
        self.record.refresh_from_db()
        self.assertEqual(self.record.user, self.other)
        self.assertEqual(self.record.created_by, self.member)
        self.assertEqual(self.record.amount, 200)
        self.client.post(
            reverse('funds:edit_record', args=[self.record.pk]),
            {
                **self.data,
                'owner': self.member.username,
            },
        )
        self.record.refresh_from_db()
        self.assertEqual(self.record.user, self.member)
        self.assertEqual(self.record.created_by, self.member)

    def test_csv_checks_each_owner_and_records_creator(self):
        self.client.force_login(self.member)
        content = (
            b'bank,category,amount,owner\n'
            b'ICBC,CURRENT,200,member\n'
            b'ICBC,CURRENT,300,other\n'
            b'ICBC,CURRENT,400,missing\n'
        )
        self.client.post(
            reverse('funds:upload_csv'),
            {
                'csv_file': SimpleUploadedFile('assets.csv', content),
            },
        )
        self.assertEqual(FundRecord.objects.count(), 2)
        self.assertEqual(
            FundRecord.objects.latest('pk').created_by, self.member
        )
        self.client.force_login(self.manager)
        self.client.post(
            reverse('funds:upload_csv'),
            {
                'csv_file': SimpleUploadedFile('assets.csv', content),
            },
        )
        self.assertEqual(FundRecord.objects.count(), 4)
        self.assertEqual(FundRecord.objects.latest('pk').user, self.other)

    def test_owner_display_tracks_account_and_audit_is_safe(self):
        self.other.username = 'renamed'
        self.other.save()
        self.record.refresh_from_db()
        self.assertEqual(self.record.owner_display, '母亲')
        legacy = FundRecord.objects.create(
            owner='member',
            bank='ICBC',
            category='CURRENT',
            amount=50,
        )
        unknown = FundRecord.objects.create(
            owner='unknown',
            bank='ICBC',
            category='CURRENT',
            amount=60,
        )
        call_command('audit_asset_owners', stdout=io.StringIO())
        legacy.refresh_from_db()
        self.assertIsNone(legacy.user_id)
        for _ in range(2):
            call_command('audit_asset_owners', '--apply', stdout=io.StringIO())
        legacy.refresh_from_db()
        unknown.refresh_from_db()
        self.record.refresh_from_db()
        self.assertEqual(legacy.user, self.member)
        self.assertIsNone(legacy.created_by_id)
        self.assertIsNone(unknown.user_id)
        self.assertEqual(self.record.user, self.other)

    def test_staff_admin_cannot_change_or_bulk_delete_other_assets(self):
        self.member.is_staff = True
        self.member.save()
        self.member.user_permissions.set(
            Permission.objects.filter(
                content_type__app_label='funds',
            )
        )
        self.client.force_login(self.member)
        response = self.client.post(
            reverse('admin:funds_fundrecord_change', args=[self.record.pk]),
            {**self.data, 'user': self.member.pk, '_save': '保存'},
        )
        self.assertEqual(response.status_code, 403)
        self.client.post(
            reverse('admin:funds_fundrecord_changelist'),
            {
                'action': 'delete_selected',
                '_selected_action': [self.record.pk],
                'post': 'yes',
            },
        )
        self.assertTrue(FundRecord.objects.filter(pk=self.record.pk).exists())

    def test_unapproved_member_cannot_write(self):
        UserProfile.objects.filter(user=self.member).update(is_approved=False)
        self.client.force_login(self.member)
        self.client.post(reverse('funds:add_record'), self.data)
        self.assertEqual(FundRecord.objects.count(), 1)

    def test_staff_list_edit_cannot_change_other_assets(self):
        self.member.is_staff = True
        self.member.save()
        self.member.user_permissions.set(
            Permission.objects.filter(
                content_type__app_label='funds',
            )
        )
        self.client.force_login(self.member)
        self.client.post(
            reverse('admin:funds_fundrecord_changelist'),
            {
                '_save': '保存',
                'form-TOTAL_FORMS': '1',
                'form-INITIAL_FORMS': '1',
                'form-MAX_NUM_FORMS': '1000',
                'form-0-id': self.record.pk,
                'form-0-savings_status': 'WITHDRAWN',
            },
        )
        self.record.refresh_from_db()
        self.assertEqual(self.record.savings_status, 'ACTIVE')

    def test_staff_can_edit_own_asset_but_cannot_transfer_it(self):
        self.record.user = self.member
        self.record.save()
        self.member.is_staff = True
        self.member.save()
        self.member.user_permissions.set(
            Permission.objects.filter(
                content_type__app_label='funds',
            )
        )
        self.client.force_login(self.member)
        url = reverse('admin:funds_fundrecord_change', args=[self.record.pk])
        self.client.post(
            url,
            {
                **self.data,
                'user': self.other.pk,
                'savings_status': 'ACTIVE',
            },
        )
        self.record.refresh_from_db()
        self.assertEqual(self.record.user, self.member)
        self.client.post(
            url,
            {
                **self.data,
                'user': self.member.pk,
                'savings_status': 'ACTIVE',
            },
        )
        self.record.refresh_from_db()
        self.assertEqual(self.record.amount, 200)

    def test_guest_demo_keeps_owner_display(self):
        response = self.client.get(reverse('funds:record_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '张三')

    def test_list_permissions_do_not_query_per_record(self):
        FundRecord.objects.bulk_create(
            [
                FundRecord(
                    user=self.member,
                    bank='ICBC',
                    category='CURRENT',
                    amount=100,
                )
                for _ in range(20)
            ]
        )
        self.client.force_login(self.member)
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(reverse('funds:record_list'))
        self.assertEqual(response.status_code, 200)
        profile_queries = [
            query
            for query in queries
            if 'accounts_userprofile' in query['sql']
        ]
        self.assertLessEqual(len(profile_queries), 5)

    def test_staff_list_edit_can_save_own_row_with_other_rows_unchanged(self):
        own = FundRecord.objects.create(
            user=self.member,
            bank='ICBC',
            category='CURRENT',
            amount=100,
        )
        self.member.is_staff = True
        self.member.save()
        self.member.user_permissions.set(
            Permission.objects.filter(
                content_type__app_label='funds',
            )
        )
        self.client.force_login(self.member)
        self.client.post(
            reverse('admin:funds_fundrecord_changelist'),
            {
                '_save': '保存',
                'form-TOTAL_FORMS': '2',
                'form-INITIAL_FORMS': '2',
                'form-MAX_NUM_FORMS': '1000',
                'form-0-id': own.pk,
                'form-0-savings_status': 'WITHDRAWN',
                'form-1-id': self.record.pk,
                'form-1-savings_status': 'ACTIVE',
            },
        )
        own.refresh_from_db()
        self.record.refresh_from_db()
        self.assertEqual(own.savings_status, 'WITHDRAWN')
        self.assertEqual(self.record.savings_status, 'ACTIVE')
