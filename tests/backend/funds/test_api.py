import json

from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import UserProfile
from funds.models import FundRecord


class FundApiTests(TestCase):
    def setUp(self):
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
            user=self.other,
            created_by=self.other,
            bank="ICBC",
            category="CURRENT",
            amount="12.34",
        )

    def write(self, path, data, method="post"):
        return getattr(self.client, method)(
            path, json.dumps(data), content_type="application/json"
        )

    def test_list_is_shared_but_other_assets_are_read_only(self):
        self.client.force_login(self.member)
        response = self.client.get("/api/v1/funds/")
        self.assertEqual(response.status_code, 200)
        row = response.json()["results"][0]
        self.assertEqual(row["amount"], "12.34")
        self.assertFalse(row["can_edit"])
        self.assertEqual(
            self.write(
                f"/api/v1/funds/{self.asset.pk}/", {"amount": "99"}, "patch"
            ).status_code,
            403,
        )

    def test_member_cannot_assign_others_and_manager_patch_preserves_fields(
        self,
    ):
        self.client.force_login(self.member)
        data = {
            "owner_id": self.other.pk,
            "bank": "CCB",
            "category": "CURRENT",
            "amount": "0",
        }
        self.assertEqual(self.write("/api/v1/funds/", data).status_code, 400)
        data["owner_id"] = self.member.pk
        response = self.write("/api/v1/funds/", data)
        self.assertEqual(response.status_code, 201)
        self.client.force_login(self.manager)
        response = self.write(
            f"/api/v1/funds/{self.asset.pk}/",
            {
                "owner_id": self.member.pk,
                "amount": "25.26",
            },
            "patch",
        )
        self.assertEqual(response.status_code, 200)
        self.asset.refresh_from_db()
        self.assertEqual(str(self.asset.amount), "25.26")
        self.assertEqual(self.asset.bank, "ICBC")
        self.assertEqual(self.asset.user, self.member)
        self.assertEqual(self.asset.created_by, self.other)

    def test_pagination_and_forged_fields_are_validated(self):
        self.client.force_login(self.manager)
        self.assertEqual(
            self.client.get(
                "/api/v1/funds/",
                {
                    "page_size": 0,
                },
            ).status_code,
            400,
        )
        self.assertEqual(
            self.write(
                "/api/v1/funds/",
                {
                    "created_by": self.member.pk,
                    "amount": 2,
                },
            ).status_code,
            400,
        )
        result = self.client.get("/api/v1/funds/", {"page_size": 1}).json()
        self.assertEqual(result["count"], 1)
        self.assertEqual(len(result["results"]), 1)

    def test_non_savings_are_unpaged_while_savings_use_pages(self):
        self.client.force_login(self.manager)
        FundRecord.objects.bulk_create(
            FundRecord(
                user=self.other, bank="CCB", category="FUND", amount="20"
            )
            for _ in range(100)
        )
        for amount in ("30", "40"):
            FundRecord.objects.create(
                user=self.other, bank="ICBC", category="SAVINGS", amount=amount
            )

        non_savings = self.client.get(
            "/api/v1/funds/",
            {"category_group": "non_savings", "page": 2, "page_size": 1},
        ).json()
        self.assertEqual(non_savings["count"], 101)
        self.assertEqual(len(non_savings["results"]), 101)
        self.assertTrue(
            all(row["category"] != "SAVINGS" for row in non_savings["results"])
        )

        savings = self.client.get(
            "/api/v1/funds/",
            {"category_group": "savings", "page": 2, "page_size": 1},
        ).json()
        self.assertEqual(savings["count"], 2)
        self.assertEqual(len(savings["results"]), 1)
        self.assertEqual(savings["results"][0]["category"], "SAVINGS")
