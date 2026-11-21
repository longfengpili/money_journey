import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.db import DatabaseError
from django.test import TestCase

from accounts.models import UserProfile
from funds.models import FundRecord, FundSnapshot


class MemberApiTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user("manager")
        UserProfile.objects.create(
            user=self.manager, is_approved=True, is_family_admin=True
        )
        self.member = User.objects.create_user("member", first_name="原姓名")
        UserProfile.objects.create(user=self.member, is_approved=True)
        self.client.force_login(self.manager)

    def test_manager_updates_member_name_and_account_states(self):
        response = self.client.patch(
            f"/api/v1/members/{self.member.pk}/",
            json.dumps({
                "first_name": "新姓名", "is_active": False,
                "is_approved": False, "is_family_admin": True,
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.member.refresh_from_db()
        self.member.userprofile.refresh_from_db()
        self.assertEqual(self.member.first_name, "新姓名")
        self.assertFalse(self.member.is_active)
        self.assertFalse(self.member.userprofile.is_approved)
        self.assertTrue(self.member.userprofile.is_family_admin)

    def test_member_changes_reject_forged_fields_and_self_lockout(self):
        endpoint = f"/api/v1/members/{self.member.pk}/"
        for payload in ({"is_superuser": True}, {"is_active": "false"}):
            response = self.client.patch(
                endpoint, json.dumps(payload), content_type="application/json"
            )
            self.assertEqual(response.status_code, 400)
        response = self.client.patch(
            f"/api/v1/members/{self.manager.pk}/",
            json.dumps({"is_active": False}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.client.force_login(self.member)
        self.assertEqual(self.client.patch(
            endpoint, json.dumps({"first_name": "越权"}),
            content_type="application/json",
        ).status_code, 403)

    def test_member_delete_transfers_assets_and_archives_source(self):
        asset = FundRecord.objects.create(
            user=self.member, bank="ICBC", category="SAVINGS", amount=10,
        )
        endpoint = f"/api/v1/members/{self.member.pk}/"
        response = self.client.delete(endpoint)
        self.assertEqual(response.status_code, 400)
        self.assertTrue(User.objects.filter(pk=self.member.pk).exists())
        self.assertTrue(FundRecord.objects.filter(pk=asset.pk).exists())
        response = self.client.delete(
            endpoint, json.dumps({"recipient_id": self.manager.pk}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.member.refresh_from_db()
        self.member.userprofile.refresh_from_db()
        self.assertFalse(self.member.is_active)
        self.assertFalse(self.member.userprofile.is_approved)
        self.assertTrue(self.member.userprofile.is_archived)
        self.assertTrue(FundRecord.objects.filter(pk=asset.pk).exists())
        asset.refresh_from_db()
        self.assertEqual(asset.user, self.manager)
        self.assertEqual(asset.owner, self.manager.username)
        self.assertNotIn(
            self.member.pk,
            [
                row["id"] for row in self.client.get(
                    "/api/v1/members/"
                ).json()["results"]
            ],
        )
        self.assertNotIn(
            self.member.pk,
            [
                row["id"] for row in self.client.get(
                    "/api/v1/funds/options/"
                ).json()["members"]
            ],
        )

    def test_member_delete_preserves_snapshot_history_and_admin(self):
        snapshot = FundSnapshot.objects.create(
            user=self.member, created_by=self.manager,
            total_amount=10, record_count=1,
        )
        self.assertEqual(self.client.delete(
            f"/api/v1/members/{self.member.pk}/",
            json.dumps({"recipient_id": self.manager.pk}),
            content_type="application/json",
        ).status_code, 200)
        self.assertTrue(FundSnapshot.objects.filter(pk=snapshot.pk).exists())
        self.assertEqual(self.client.delete(
            f"/api/v1/members/{self.manager.pk}/",
            json.dumps({"recipient_id": self.member.pk}),
            content_type="application/json",
        ).status_code, 400)

    def test_member_delete_blocks_legacy_assets_and_non_admin(self):
        legacy = FundRecord.objects.create(
            owner=self.member.username, bank="ICBC",
            category="CURRENT", amount=8,
        )
        endpoint = f"/api/v1/members/{self.member.pk}/"
        self.assertEqual(self.client.delete(endpoint).status_code, 400)
        self.assertTrue(FundRecord.objects.filter(pk=legacy.pk).exists())
        self.client.force_login(self.member)
        self.assertEqual(self.client.delete(endpoint).status_code, 403)
        self.client.force_login(self.manager)
        self.assertEqual(self.client.delete(
            endpoint, json.dumps({"recipient_id": self.manager.pk}),
            content_type="application/json",
        ).status_code, 200)
        legacy.refresh_from_db()
        self.assertEqual(legacy.user, self.manager)

    def test_member_delete_rejects_invalid_recipient(self):
        endpoint = f"/api/v1/members/{self.member.pk}/"
        inactive = User.objects.create_user("inactive", is_active=False)
        UserProfile.objects.create(user=inactive, is_approved=True)
        archived = User.objects.create_user("archived")
        UserProfile.objects.create(
            user=archived, is_approved=True, is_archived=True
        )
        for recipient in (
            self.member.pk, 999999, "invalid", inactive.pk, archived.pk
        ):
            response = self.client.delete(
                endpoint, json.dumps({"recipient_id": recipient}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 400)
        self.member.refresh_from_db()
        self.assertTrue(self.member.is_active)

    def test_member_transfer_rolls_back_when_archive_fails(self):
        asset = FundRecord.objects.create(
            user=self.member, bank="ICBC", category="CURRENT", amount=12,
        )
        with patch.object(
            UserProfile, "save", side_effect=DatabaseError("test failure")
        ), self.assertLogs("money_journey.api.base", level="ERROR"):
            response = self.client.delete(
                f"/api/v1/members/{self.member.pk}/",
                json.dumps({"recipient_id": self.manager.pk}),
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 500)
        asset.refresh_from_db()
        self.member.refresh_from_db()
        self.assertEqual(asset.user, self.member)
        self.assertTrue(self.member.is_active)

    def test_superuser_cannot_be_edited_on_family_page(self):
        admin = User.objects.create_superuser("admin", password="safe-password")
        response = self.client.patch(
            f"/api/v1/members/{admin.pk}/",
            json.dumps({"is_active": False}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        admin.refresh_from_db()
        self.assertTrue(admin.is_active)

    def test_registration_requires_approval_and_profile_failure_rolls_back(
        self,
    ):
        data = {
            "username": "new_member",
            "first_name": "新成员",
            "password1": "Safe-long-password-963!",
            "password2": "Safe-long-password-963!",
        }
        response = self.client.post(
            "/api/v1/auth/register/",
            json.dumps(data),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        user = User.objects.get(username="new_member")
        self.assertFalse(user.userprofile.is_approved)
        data["username"] = "rollback_member"
        with patch(
            "accounts.models.UserProfile.objects.create",
            side_effect=DatabaseError("fixture"),
        ), self.assertLogs("money_journey.api.base", level="ERROR"):
            response = self.client.post(
                "/api/v1/auth/register/",
                json.dumps(data),
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 500)
        self.assertFalse(
            User.objects.filter(username="rollback_member").exists()
        )

    def test_manager_creates_unusable_account_and_approves_registration(self):
        response = self.client.post(
            "/api/v1/members/",
            json.dumps(
                {
                    "username": "father",
                    "first_name": "父亲",
                    "is_superuser": True,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        user = User.objects.get(username="father")
        self.assertFalse(user.has_usable_password())
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.userprofile.is_approved)
        user.userprofile.is_approved = False
        user.userprofile.save()
        self.assertEqual(
            self.client.post(f"/api/v1/approvals/{user.pk}/").status_code, 200
        )
        self.client.force_login(user)
        self.assertEqual(self.client.get("/api/v1/members/").status_code, 403)
