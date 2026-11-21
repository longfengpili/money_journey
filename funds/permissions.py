"""各写入入口共用资产所有者解析。"""

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied

from accounts.permissions import can_write_assets, is_family_admin


def resolve_record_owner(actor, username, current_owner=None):
    if not can_write_assets(actor):
        raise PermissionDenied('账号尚未批准或已停用')
    username = (username or '').strip()
    if not is_family_admin(actor):
        if username and username != actor.username:
            raise PermissionDenied('只能为自己录入或修改资产')
        return actor
    if not username:
        return current_owner or actor
    try:
        return User.objects.get(username=username)
    except User.DoesNotExist as exc:
        raise ValueError(f'所有者“{username}”不存在') from exc
