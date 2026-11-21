"""总览 JSON 适配，复用现有统计并保留游客演示。"""

from copy import deepcopy
from decimal import Decimal

from django.contrib.auth.models import User
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import can_write_assets
from analytics.demo import DEMO_DATA, demo_maturity_summary
from analytics.queries import (
    get_maturity_summary,
    get_snapshot_trend,
    normalize_filters,
    summarize_assets,
)
from funds.models import FundRecord
from money_journey.api.base import encode_values


def selected_owner(params):
    value = params.get("owner_id", "")
    if not value:
        return None
    try:
        value = int(value)
        if value < 1:
            raise ValueError
        return value
    except (TypeError, ValueError):
        raise ValidationError({"owner_id": ["请选择有效成员"]})


def member_choices():
    return list(
        User.objects.exclude(userprofile__is_archived=True).order_by(
            "username"
        ).values(
            "id", "username", "first_name"
        )
    )


class SummaryApi(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        demo = not request.user.is_authenticated
        if not demo and not can_write_assets(request.user):
            raise PermissionDenied()
        if demo:
            data = {
                key: deepcopy(DEMO_DATA[key])
                for key in (
                    "owner_summary",
                    "owner_category_summary",
                    "bank_summary",
                    "category_summary",
                    "status_summary",
                    "total_amount",
                    "total_records",
                    "owner_count",
                )
            }
            # 演示银行维度与既有图表一致，保证各维度合计相同。
            data["bank_summary"][-1]["total_amount"] = 0
            for key in (
                "owner_summary",
                "owner_category_summary",
                "bank_summary",
                "category_summary",
                "status_summary",
            ):
                for row in data[key]:
                    row["total_amount"] = Decimal(str(row["total_amount"]))
            data["total_amount"] = Decimal(str(data["total_amount"]))
            data["maturity_summary"] = demo_maturity_summary()
        else:
            data = summarize_assets(
                request.GET, owner_id=selected_owner(request.GET)
            )
            data["maturity_summary"] = get_maturity_summary(
                request.GET, owner_id=selected_owner(request.GET)
            )
        data.update(
            {
                "demo": demo,
                "owner_choices": [] if demo else member_choices(),
                "bank_choices": FundRecord.BANK_CHOICES,
                "category_choices": FundRecord.CATEGORY_CHOICES,
                "status_choices": FundRecord.SAVINGS_STATUS_CHOICES,
                "filters": normalize_filters({} if demo else request.GET),
            }
        )
        return Response(encode_values(data))


class TrendApi(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        if not request.user.is_authenticated:
            return Response({"results": [], "demo": True})
        if not can_write_assets(request.user):
            raise PermissionDenied()
        rows = get_snapshot_trend(
            request.GET.get("owner", ""), owner_id=selected_owner(request.GET)
        )
        return Response(encode_values({"results": rows, "demo": False}))
