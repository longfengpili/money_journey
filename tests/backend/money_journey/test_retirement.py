"""旧页面退役后，书签跳转与旧提交入口无副作用。"""

from django.contrib.auth.models import User
from django.test import Client, TestCase

from accounts.models import UserProfile
from funds.models import FundRecord, FundSnapshot


class RetiredPageTests(TestCase):
    def test_old_submissions_keep_csrf_protection(self):
        client = Client(enforce_csrf_checks=True)
        path = "/savings-calculator/calculate/"
        self.assertEqual(client.post(path).status_code, 403)
        context = client.get("/api/v1/auth/context/").json()
        response = client.post(
            path, {"csrfmiddlewaretoken": context["csrf_token"]}
        )
        self.assertEqual(response.status_code, 410)

    def test_old_get_routes_redirect_to_new_pages_and_keep_filters(self):
        for old, new in (
            ("/legacy/", "/app/"),
            ("/accounts/login/", "/app/login"),
            ("/accounts/register/", "/app/register"),
            ("/accounts/approval/", "/app/members"),
            ("/accounts/members/create/", "/app/members"),
            ("/accounts/approve/1/", "/app/members"),
            ("/accounts/logout/", "/app/login"),
            ("/funds/?bank=ICBC", "/app/funds?bank=ICBC"),
            ("/funds/add/", "/app/funds"),
            ("/funds/1/edit/", "/app/funds"),
            ("/funds/upload-csv/", "/app/operations"),
            ("/funds/create-snapshot/", "/app/operations"),
            ("/funds/download-template/", "/api/v1/funds/import-template/"),
            ("/analytics/dashboard/", "/app/"),
            ("/analytics/charts/", "/app/"),
            ("/savings-calculator/", "/app/calculator"),
            ("/savings-calculator/calculate/", "/app/calculator"),
            ("/savings-calculator/results/", "/app/calculator"),
        ):
            with self.subTest(old=old):
                self.assertRedirects(
                    self.client.get(old), new, fetch_redirect_response=False
                )

    def test_old_posts_are_retired_without_writing_or_redirecting_payloads(
        self,
    ):
        for path in (
            "/funds/add/",
            "/funds/upload-csv/",
            "/accounts/register/",
            "/savings-calculator/calculate/",
        ):
            response = self.client.post(path, {"amount": "100"})
            self.assertEqual(response.status_code, 410)
            self.assertEqual(
                response.json()["code"], "LEGACY_ENDPOINT_RETIRED"
            )
        self.assertEqual(FundRecord.objects.count(), 0)

    def test_authenticated_old_posts_do_not_change_accounts_or_assets(self):
        manager = User.objects.create_user("manager")
        UserProfile.objects.create(
            user=manager,
            is_approved=True,
            is_family_admin=True,
        )
        self.client.force_login(manager)
        for path in (
            "/accounts/members/create/",
            "/accounts/approve/1/",
            "/accounts/logout/",
            "/accounts/login/",
            "/funds/create-snapshot/",
            "/funds/1/edit/",
            "/funds/add/",
            "/funds/upload-csv/",
        ):
            with self.subTest(path=path):
                response = self.client.post(path, {"username": "unwanted"})
                self.assertEqual(response.status_code, 410)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(FundRecord.objects.count(), 0)
        self.assertEqual(FundSnapshot.objects.count(), 0)
        self.assertEqual(int(self.client.session["_auth_user_id"]), manager.pk)
