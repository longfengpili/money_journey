from django.test import TestCase, override_settings


class FrontendRoutingTests(TestCase):
    @override_settings(FRONTEND_ENABLED=True)
    def test_root_switches_to_app_and_legacy_page_stays_available(self):
        self.assertRedirects(
            self.client.get("/"), "/app/", fetch_redirect_response=False
        )
        self.assertEqual(self.client.get("/legacy/").status_code, 200)

    @override_settings(FRONTEND_ENABLED=False)
    def test_rollback_returns_original_home(self):
        self.assertEqual(self.client.get("/").status_code, 200)
