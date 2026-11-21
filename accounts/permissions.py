"""家庭资产权限的统一判定。"""

from accounts.models import UserProfile


def can_write_assets(user):
    if not user.is_authenticated or not user.is_active:
        return False
    return (
        user.is_superuser
        or UserProfile.objects.filter(
            user=user,
            is_approved=True,
        ).exists()
    )


def is_family_admin(user):
    return can_write_assets(user) and (
        user.is_superuser
        or UserProfile.objects.filter(
            user=user,
            is_family_admin=True,
        ).exists()
    )


def can_edit_record(user, record):
    return can_write_assets(user) and (
        is_family_admin(user) or record.user_id == user.pk
    )
