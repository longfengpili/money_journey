"""注册、家庭成员与批准接口。"""

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.forms import CreateMemberForm, RegistrationForm
from accounts.models import UserProfile
from accounts.permissions import can_write_assets
from accounts.services import save_registration
from funds.models import FundRecord
from money_journey.api.base import FamilyAdmin, FamilyAPIView


def valid_form(form):
    if not form.is_valid():
        raise ValidationError(
            {key: list(value) for key, value in form.errors.items()}
        )


@method_decorator(csrf_protect, name="dispatch")
class RegisterApi(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        if not isinstance(request.data, dict):
            raise ValidationError({"__all__": ["请求格式错误"]})
        form = RegistrationForm(request.data)
        valid_form(form)
        user = save_registration(form)
        return Response(
            {"id": user.pk, "message": "注册成功，请等待家庭管理员批准"},
            status=201,
        )


class MembersApi(FamilyAPIView):
    permission_classes = [FamilyAdmin]

    def get(self, request):
        rows = []
        for user in User.objects.select_related("userprofile").exclude(
            userprofile__is_archived=True
        ).order_by("pk"):
            profile = getattr(user, "userprofile", None)
            rows.append(
                {
                    "id": user.pk,
                    "username": user.username,
                    "first_name": user.first_name,
                    "is_approved": user.is_superuser
                    or bool(profile and profile.is_approved),
                    "is_family_admin": user.is_superuser
                    or bool(profile and profile.is_family_admin),
                    "is_superuser": user.is_superuser,
                    "is_active": user.is_active,
                    "has_login": user.has_usable_password(),
                }
            )
        return Response({"results": rows})

    @transaction.atomic
    def post(self, request):
        if not isinstance(request.data, dict):
            raise ValidationError({"__all__": ["请求格式错误"]})
        form = CreateMemberForm(request.data)
        valid_form(form)
        user = form.save(commit=False)
        user.set_unusable_password()
        user.save()
        UserProfile.objects.create(user=user, is_approved=True)
        return Response(
            {"id": user.pk, "message": "家庭成员已创建"}, status=201
        )


class MemberDetailApi(FamilyAPIView):
    permission_classes = [FamilyAdmin]

    @transaction.atomic
    def patch(self, request, pk):
        user = get_object_or_404(
            User.objects.select_for_update().exclude(
                userprofile__is_archived=True
            ), pk=pk
        )
        if user.is_superuser:
            raise PermissionDenied("超级管理员账号请在 Django 后台管理")
        if not isinstance(request.data, dict):
            raise ValidationError({"__all__": ["请求格式错误"]})
        allowed = {"first_name", "is_active", "is_approved", "is_family_admin"}
        if not request.data or set(request.data) - allowed:
            raise ValidationError({"__all__": ["包含不允许修改的字段"]})
        profile = get_object_or_404(
            UserProfile.objects.select_for_update(), user=user
        )
        if user.pk == request.user.pk and any(
            request.data.get(key) is False
            for key in ("is_active", "is_approved", "is_family_admin")
        ):
            raise ValidationError({"__all__": ["不能停用或取消自己的管理权限"]})
        if "first_name" in request.data:
            name = request.data["first_name"]
            if not isinstance(name, str) or len(name) > 150:
                raise ValidationError({"first_name": ["姓名长度不能超过 150 字"]})
            user.first_name = name.strip()
            user.save(update_fields=["first_name"])
        for key in ("is_active", "is_approved", "is_family_admin"):
            if key not in request.data:
                continue
            value = request.data[key]
            if type(value) is not bool:
                raise ValidationError({key: ["请选择有效状态"]})
            if key == "is_active":
                user.is_active = value
                user.save(update_fields=[key])
            else:
                setattr(profile, key, value)
                profile.save(update_fields=[key])
        return Response({"message": "成员信息已更新"})

    @transaction.atomic
    def delete(self, request, pk):
        user = get_object_or_404(
            User.objects.select_for_update().exclude(
                userprofile__is_archived=True
            ), pk=pk
        )
        if user.pk == request.user.pk or user.is_superuser:
            raise ValidationError({"__all__": ["不能删除当前账号或超级管理员"]})
        if not isinstance(request.data, dict) or set(request.data) != {
            "recipient_id"
        }:
            raise ValidationError({"recipient_id": ["请选择接收资产的成员"]})
        recipient_id = request.data["recipient_id"]
        if type(recipient_id) is not int or recipient_id == user.pk:
            raise ValidationError({"recipient_id": ["请选择其他有效成员"]})
        recipient = User.objects.select_for_update().exclude(
            userprofile__is_archived=True
        ).filter(pk=recipient_id, is_active=True).first()
        if recipient is None or not can_write_assets(recipient):
            raise ValidationError({"recipient_id": ["请选择已批准的有效成员"]})
        profile = get_object_or_404(
            UserProfile.objects.select_for_update(), user=user
        )
        records = FundRecord.objects.filter(
            Q(user=user) | Q(user__isnull=True, owner=user.username)
        )
        transferred = records.update(
            user=recipient, owner=recipient.username, updated_at=timezone.now()
        )
        user.is_active = False
        user.save(update_fields=["is_active"])
        profile.is_approved = False
        profile.is_family_admin = False
        profile.is_archived = True
        profile.save(update_fields=[
            "is_approved", "is_family_admin", "is_archived"
        ])
        return Response({
            "message": "家庭成员已移除，资产已转移",
            "transferred_records": transferred,
        })


class ApprovalApi(FamilyAPIView):
    permission_classes = [FamilyAdmin]

    @transaction.atomic
    def post(self, request, pk):
        profile = get_object_or_404(
            UserProfile.objects.select_for_update().filter(is_archived=False),
            user_id=pk,
        )
        profile.is_approved = True
        profile.save(update_fields=["is_approved"])
        return Response({"message": "账号已批准"})
