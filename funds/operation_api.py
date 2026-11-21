"""CSV 和当天快照的 JSON 适配。"""

from dataclasses import asdict

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from funds.importers import import_fund_csv
from funds.snapshots import refresh_daily_snapshots
from funds.views import download_csv_template
from money_journey.api.base import FamilyAdmin, FamilyAPIView


class ImportApi(FamilyAPIView):
    parser_classes = [MultiPartParser]

    def post(self, request):
        upload = request.FILES.get("csv_file")
        if upload is None:
            raise ValidationError({"csv_file": ["请选择 CSV 文件"]})
        try:
            result = import_fund_csv(upload, actor=request.user)
        except DjangoValidationError as exc:
            raise ValidationError({"csv_file": exc.messages})
        return Response(asdict(result))


class ImportTemplateApi(FamilyAPIView):
    def get(self, request):
        return download_csv_template(request._request)


class SnapshotRefreshApi(FamilyAPIView):
    permission_classes = [FamilyAdmin]

    def post(self, request):
        try:
            result = refresh_daily_snapshots(request.user)
        except DjangoValidationError as exc:
            raise ValidationError({"__all__": exc.messages})
        return Response(asdict(result))
