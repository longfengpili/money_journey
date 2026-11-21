from django.test import TestCase


class FrontendRoutingTests(TestCase):
    def test_root_opens_component_frontend(self):
        self.assertRedirects(
            self.client.get("/"), "/app/", fetch_redirect_response=False
        )

    def test_legacy_home_opens_component_frontend(self):
        self.assertRedirects(
            self.client.get("/legacy/"),
            "/app/",
            fetch_redirect_response=False,
        )
