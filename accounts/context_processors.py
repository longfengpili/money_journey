from accounts.permissions import is_family_admin


def family_permissions(request):
    return {'is_family_admin': is_family_admin(request.user)}
