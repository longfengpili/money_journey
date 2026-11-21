"""同域会话登录；匿名登录和登出同样校验 CSRF。"""

import json

from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET, require_POST

from accounts.permissions import can_write_assets, is_family_admin
from .base import error_response


def auth_context(request):
    user = request.user
    authenticated = user.is_authenticated
    return {
        'user': {
            'id': user.pk, 'username': user.username,
            'name': user.first_name.strip() or user.username,
        } if authenticated else None,
        'capabilities': {
            'write_assets': can_write_assets(user),
            'manage_family': is_family_admin(user),
        },
        'csrf_token': get_token(request),
    }


@never_cache
@require_GET
def context(request):
    return JsonResponse(auth_context(request))


@never_cache
@require_POST
@csrf_protect
def sign_in(request):
    try:
        data = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        return error_response('VALIDATION_ERROR', '请求格式错误')
    if not isinstance(data, dict) or not all(
        isinstance(data.get(key), str) for key in ('username', 'password')
    ):
        return error_response('VALIDATION_ERROR', '请输入用户名和密码')
    form = AuthenticationForm(request, data=data)
    if not form.is_valid():
        return error_response('INVALID_LOGIN', '用户名或密码错误，或账号已停用')
    user = form.get_user()
    if not can_write_assets(user):
        return error_response('APPROVAL_PENDING', '账号尚未批准，请联系家庭管理员',
                              status=403)
    login(request, user)
    request.session.pop('frontend_calculation', None)
    return JsonResponse(auth_context(request))


@never_cache
@require_POST
@csrf_protect
def sign_out(request):
    logout(request)
    return JsonResponse(auth_context(request))
