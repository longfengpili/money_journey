from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from funds.models import FundRecord, FundSnapshot
from funds import test_api


class OperationApiTests(TestCase):
    setUp = test_api.FundApiTests.setUp

    def test_csv_reports_invalid_rows_and_preserves_valid_batch(self):
        self.client.force_login(self.member)
        response = self.client.post('/api/v1/funds/import/', {
            'csv_file': SimpleUploadedFile('sample.csv', (
                'bank,category,amount\nICBC,CURRENT,0\nICBC,CURRENT,-1\n'
            ).encode()),
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['success_count'], 1)
        self.assertEqual(response.json()['error_count'], 1)
        self.assertEqual(FundRecord.objects.filter(user=self.member).count(), 1)

    def test_only_manager_can_refresh_and_repeat_updates_original_rows(self):
        self.client.force_login(self.member)
        self.assertEqual(self.client.post('/api/v1/snapshots/refresh/')
                         .status_code, 403)
        self.client.force_login(self.manager)
        response = self.client.post('/api/v1/snapshots/refresh/')
        self.assertEqual(response.status_code, 200)
        ids = list(FundSnapshot.objects.values_list('pk', flat=True))
        self.client.post('/api/v1/snapshots/refresh/')
        self.assertEqual(list(FundSnapshot.objects.values_list('pk', flat=True)),
                         ids)
