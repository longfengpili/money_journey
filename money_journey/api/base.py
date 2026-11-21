"""接口权限、金额编码及统一异常响应。"""

import logging
from decimal import Decimal

from django.http import JsonResponse
from django.views.csrf import csrf_failure as django_csrf_failure
from rest_framework.exceptions import NotAuthenticated, PermissionDenied
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView, exception_handler

from accounts.permissions import can_write_assets, is_family_admin

logger = logging.getLogger(__name__)


def encode_values(value):
    if isinstance(value, Decimal):
        return format(value, ".2f")
    if isinstance(value, dict):
        return {key: encode_values(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [encode_values(item) for item in value]
    return value


def error_response(code, message, *, fields=None, status=400):
    return JsonResponse(
        {
            "code": code,
            "message": message,
            "fields": fields or {},
        },
        status=status,
    )


def csrf_failure(request, reason=""):
    if request.path.startswith("/api/"):
        return error_response(
            "CSRF_FAILED", "安全凭证已失效，请刷新后重试", status=403
        )
    return django_csrf_failure(request, reason=reason)


class ApprovedUser(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            raise NotAuthenticated("请先登录")
        return can_write_assets(request.user)


class FamilyAdmin(ApprovedUser):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and is_family_admin(
            request.user
        )


class FamilyAPIView(APIView):
    permission_classes = [ApprovedUser]


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        logger.exception("业务接口执行失败")
        return Response(
            {
                "code": "SERVER_ERROR",
                "message": "操作失败，请稍后重试",
                "fields": {},
            },
            status=500,
        )
    code = "VALIDATION_ERROR"
    message = "请检查输入"
    if isinstance(exc, NotAuthenticated):
        code, message = "AUTH_REQUIRED", "请先登录"
    elif isinstance(exc, PermissionDenied) and str(exc.detail).startswith(
        "CSRF"
    ):
        code, message = "CSRF_FAILED", "安全凭证已失效，请刷新后重试"
    elif isinstance(exc, PermissionDenied):
        code, message = "FORBIDDEN", "账号未批准、已停用或没有此操作权限"
    elif response.status_code == 403:
        code, message = "CSRF_FAILED", "安全凭证已失效，请刷新后重试"
    elif response.status_code == 404:
        code, message = "NOT_FOUND", "记录不存在"
    elif response.status_code == 405:
        code, message = "METHOD_NOT_ALLOWED", "不支持此操作方式"
    fields = response.data if code == "VALIDATION_ERROR" else {}
    response.data = {"code": code, "message": message, "fields": fields}
    return response
