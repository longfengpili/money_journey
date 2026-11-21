"""资产 JSON 接口，所有写入复用页面表单和归属规则。"""

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
from django.forms.models import model_to_dict
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from accounts.permissions import can_edit_record, is_family_admin
from analytics.api import member_choices, selected_owner
from funds.forms import FundRecordForm
from funds.models import FundRecord
from money_journey.api.base import FamilyAPIView, encode_values


def record_data(record, actor, family_admin):
    return {
        "id": record.pk,
        "user_id": record.user_id,
        "owner": record.owner,
        "owner_display": record.owner_display,
        "bank": record.bank,
        "bank_display": record.get_bank_display(),
        "category": record.category,
        "category_display": record.get_category_display(),
        "savings_status": record.savings_status,
        "status_display": record.get_savings_status_display(),
        "amount": record.amount,
        "interest_rate": record.interest_rate,
        "deposit_period": record.deposit_period,
        "due_date": record.due_date,
        "start_date": record.start_date,
        "updated_at": record.updated_at,
        "can_edit": family_admin or record.user_id == actor.pk,
    }


def positive_integer(params, key, default, maximum=None):
    try:
        value = int(params.get(key, default))
        if value < 1 or (maximum and value > maximum):
            raise ValueError
        return value
    except (ValueError, TypeError):
        raise ValidationError({key: ["请输入有效的正整数"]})


def asset_query(params):
    records = FundRecord.objects.select_related("user")
    owner_id = selected_owner(params)
    if owner_id is not None:
        records = records.filter(user_id=owner_id)
    owner = params.get("owner", "").strip()
    if owner:
        records = records.filter(
            Q(user__username__icontains=owner)
            | Q(user__isnull=True, owner__icontains=owner)
        )
    for field in ("bank", "category", "savings_status"):
        value = params.get(
            field, "ACTIVE" if field == "savings_status" else ""
        )
        if value:
            records = records.filter(**{field: value})
    ordering = params.get("ordering", "-amount")
    if ordering not in (
        "amount",
        "-amount",
        "due_date",
        "-due_date",
        "id",
        "-id",
    ):
        raise ValidationError({"ordering": ["排序方式不支持"]})
    return records.order_by(ordering, "pk")


def save_asset(data, actor, instance=None):
    allowed = set(FundRecordForm.Meta.fields) - {"owner"} | {"owner_id"}
    if not isinstance(data, dict):
        raise ValidationError({"__all__": ["请求应为对象"]})
    if set(data) - allowed:
        raise ValidationError({"__all__": ["包含不允许修改的字段"]})
    values = (
        model_to_dict(instance, fields=FundRecordForm.Meta.fields)
        if instance
        else {}
    )
    values["owner"] = (
        instance.user.username if instance and instance.user else ""
    )
    values.update(
        {key: value for key, value in data.items() if key != "owner_id"}
    )
    if "owner_id" in data:
        try:
            owner = User.objects.exclude(
                userprofile__is_archived=True
            ).get(pk=int(data["owner_id"]))
        except (User.DoesNotExist, TypeError, ValueError, OverflowError):
            raise ValidationError({"owner_id": ["请选择有效成员"]})
        values["owner"] = owner.username
    form = FundRecordForm(values, actor=actor, instance=instance)
    if not form.is_valid():
        errors = {
            ("owner_id" if key == "owner" else key): list(messages)
            for key, messages in form.errors.items()
        }
        raise ValidationError(errors)
    return form.save()


class FundOptionsApi(FamilyAPIView):
    def get(self, request):
        members = member_choices()
        return Response(
            {
                "members": members,
                "owners": (
                    members
                    if is_family_admin(request.user)
                    else [
                        member
                        for member in members
                        if member["id"] == request.user.pk
                    ]
                ),
                "bank_choices": FundRecord.BANK_CHOICES,
                "category_choices": FundRecord.CATEGORY_CHOICES,
                "status_choices": FundRecord.SAVINGS_STATUS_CHOICES,
            }
        )


class FundsApi(FamilyAPIView):
    def get(self, request):
        page = positive_integer(request.GET, "page", 1)
        size = positive_integer(request.GET, "page_size", 50, 100)
        records = asset_query(request.GET)
        group = request.GET.get("category_group")
        if group == "non_savings":
            records = records.exclude(category="SAVINGS")
        elif group == "savings":
            records = records.filter(category="SAVINGS")
        count = records.count()
        manager = is_family_admin(request.user)
        selected_records = (
            records
            if group == "non_savings"
            else records[(page - 1) * size:page * size]
        )
        rows = [
            record_data(row, request.user, manager)
            for row in selected_records
        ]
        return Response(
            encode_values(
                {
                    "count": count,
                    "page": 1 if group == "non_savings" else page,
                    "page_size": count if group == "non_savings" else size,
                    "results": rows,
                }
            )
        )

    @transaction.atomic
    def post(self, request):
        record = save_asset(request.data, request.user)
        return Response(
            encode_values(
                record_data(
                    record, request.user, is_family_admin(request.user)
                )
            ),
            status=201,
        )


class FundDetailApi(FamilyAPIView):
    def get(self, request, pk):
        record = get_object_or_404(
            FundRecord.objects.select_related("user"), pk=pk
        )
        return Response(
            encode_values(
                record_data(
                    record, request.user, is_family_admin(request.user)
                )
            )
        )

    @transaction.atomic
    def patch(self, request, pk):
        record = get_object_or_404(
            FundRecord.objects.select_for_update(), pk=pk
        )
        if not can_edit_record(request.user, record):
            raise PermissionDenied()
        record = save_asset(request.data, request.user, instance=record)
        return Response(
            encode_values(
                record_data(
                    record, request.user, is_family_admin(request.user)
                )
            )
        )
