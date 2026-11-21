from django.contrib.auth.models import AnonymousUser, User
from django.db import DatabaseError
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch

from accounts.models import UserProfile
from accounts.permissions import (
    can_edit_record,
    can_write_assets,
    is_family_admin,
)
from funds.models import FundRecord


class FamilyPermissionTests(TestCase):
    def setUp(self):
        self.member = User.objects.create_user("member")
        self.other = User.objects.create_user("other")
        self.manager = User.objects.create_user("manager")
        for user in (self.member, self.other, self.manager):
            UserProfile.objects.create(user=user, is_approved=True)
        self.manager.userprofile.is_family_admin = True
        self.manager.userprofile.save()
        self.record = FundRecord.objects.create(
            user=self.other,
            bank="ICBC",
            category="CURRENT",
            amount=100,
        )

    def test_permission_matrix(self):
        self.assertTrue(can_edit_record(self.other, self.record))
        self.assertFalse(can_edit_record(self.member, self.record))
        self.assertTrue(can_edit_record(self.manager, self.record))
        self.member.is_staff = True
        self.assertFalse(is_family_admin(self.member))
        self.assertFalse(can_edit_record(self.member, self.record))
        self.record.user = None
        self.assertFalse(can_edit_record(self.member, self.record))
        self.assertTrue(can_edit_record(self.manager, self.record))
        self.assertFalse(can_write_assets(AnonymousUser()))
        missing_profile = User.objects.create_user("missing")
        self.assertFalse(can_write_assets(missing_profile))
        self.other.userprofile.is_approved = False
        self.other.userprofile.save()
        self.assertFalse(can_write_assets(self.other))
        self.manager.is_active = False
        self.assertFalse(can_edit_record(self.manager, self.record))
        self.member.is_superuser = True
        self.assertTrue(can_edit_record(self.member, self.record))

    def test_manager_creates_member_without_password_or_privileges(self):
        self.client.force_login(self.manager)
        response = self.client.post(
            "/api/v1/members/",
            {
                "username": "mother",
                "first_name": "母亲",
                "is_superuser": "on",
                "is_family_admin": "on",
                "is_staff": "on",
            },
        )
        self.assertEqual(response.status_code, 201)
        user = User.objects.get(username="mother")
        self.assertFalse(user.has_usable_password())
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.userprofile.is_family_admin)
        self.assertTrue(user.userprofile.is_approved)
        self.client.post("/api/v1/members/", {"username": "mother"})
        self.assertEqual(User.objects.filter(username="mother").count(), 1)

    def test_member_cannot_create_or_approve_members(self):
        self.client.force_login(self.member)
        self.assertEqual(
            self.client.post(
                "/api/v1/members/",
                {"username": "forbidden"},
            ).status_code,
            403,
        )
        self.client.post(f"/api/v1/approvals/{self.other.pk}/")
        self.assertFalse(User.objects.filter(username="forbidden").exists())

    def test_manager_can_access_approval_and_navigation(self):
        self.client.force_login(self.manager)
        self.assertEqual(self.client.get("/api/v1/members/").status_code, 200)
        context = self.client.get("/api/v1/auth/context/").json()
        self.assertTrue(context["capabilities"]["manage_family"])

    def test_approval_admin_links_resolve_to_accessible_pages(self):
        admin = User.objects.create_superuser(
            "admin", password="test-password"
        )
        self.client.force_login(admin)
        self.assertEqual(self.client.get("/api/v1/members/").status_code, 200)
        for route in (
            "admin:auth_user_changelist",
            "admin:accounts_userprofile_changelist",
        ):
            self.assertEqual(self.client.get(reverse(route)).status_code, 200)

    def test_family_manager_sees_only_accessible_actions(self):
        self.client.force_login(self.manager)
        context = self.client.get("/api/v1/auth/context/").json()
        self.assertTrue(context["capabilities"]["manage_family"])
        self.assertFalse(self.manager.is_staff)
        self.assertEqual(self.client.get("/api/v1/members/").status_code, 200)
        self.assertEqual(self.client.get("/admin/").status_code, 302)

    def test_member_creation_rolls_back_if_profile_fails(self):
        self.client.force_login(self.manager)
        with patch(
            "accounts.api.UserProfile.objects.create",
            side_effect=DatabaseError("隔离测试写入失败"),
        ):
            with self.assertLogs("money_journey.api.base", level="ERROR"):
                response = self.client.post(
                    "/api/v1/members/", {"username": "rollback"}
                )
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["code"], "SERVER_ERROR")
        self.assertNotIn("隔离测试", response.content.decode())
        self.assertFalse(User.objects.filter(username="rollback").exists())

    def test_staff_cannot_promote_self_through_admin(self):
        from django.contrib.auth.models import Permission

        self.member.is_staff = True
        self.member.save()
        self.member.user_permissions.set(
            Permission.objects.filter(
                content_type__app_label__in=["auth", "accounts"],
            )
        )
        self.client.force_login(self.member)
        for route, pk, payload in (
            (
                "admin:accounts_userprofile_change",
                self.member.userprofile.pk,
                {
                    "user": self.member.pk,
                    "is_approved": "on",
                    "is_family_admin": "on",
                },
            ),
            (
                "admin:auth_user_change",
                self.member.pk,
                {"username": "member", "is_superuser": "on"},
            ),
        ):
            self.assertEqual(
                self.client.post(
                    reverse(route, args=[pk]), payload
                ).status_code,
                403,
            )
        self.member.refresh_from_db()
        self.member.userprofile.refresh_from_db()
        self.assertFalse(self.member.is_superuser)
        self.assertFalse(self.member.userprofile.is_family_admin)
