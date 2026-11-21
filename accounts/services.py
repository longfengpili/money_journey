"""注册的账号与资料统一事务。"""

from django.db import transaction

from accounts.models import UserProfile


@transaction.atomic
def save_registration(form):
    user = form.save()
    UserProfile.objects.create(user=user, is_approved=False)
    return user
