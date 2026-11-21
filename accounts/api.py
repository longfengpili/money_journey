"""注册、家庭成员与批准接口。"""

from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.forms import CreateMemberForm, RegistrationForm
from accounts.models import UserProfile
from accounts.services import save_registration
from money_journey.api.base import FamilyAdmin, FamilyAPIView


def valid_form(form):
    if not form.is_valid():
        raise ValidationError({key: list(value)
                               for key, value in form.errors.items()})


@method_decorator(csrf_protect, name='dispatch')
class RegisterApi(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        if not isinstance(request.data, dict):
            raise ValidationError({'__all__': ['请求格式错误']})
        form = RegistrationForm(request.data)
        valid_form(form)
        user = save_registration(form)
        return Response({'id': user.pk, 'message': '注册成功，请等待家庭管理员批准'},
                        status=201)


class MembersApi(FamilyAPIView):
    permission_classes = [FamilyAdmin]

    def get(self, request):
        rows = []
        for user in User.objects.select_related('userprofile').order_by('pk'):
            profile = getattr(user, 'userprofile', None)
            rows.append({
                'id': user.pk, 'username': user.username,
                'first_name': user.first_name,
                'is_approved': user.is_superuser or bool(
                    profile and profile.is_approved
                ),
                'is_family_admin': user.is_superuser or bool(
                    profile and profile.is_family_admin
                ),
                'is_active': user.is_active,
                'has_login': user.has_usable_password(),
            })
        return Response({'results': rows})

    @transaction.atomic
    def post(self, request):
        if not isinstance(request.data, dict):
            raise ValidationError({'__all__': ['请求格式错误']})
        form = CreateMemberForm(request.data)
        valid_form(form)
        user = form.save(commit=False)
        user.set_unusable_password()
        user.save()
        UserProfile.objects.create(user=user, is_approved=True)
        return Response({'id': user.pk, 'message': '家庭成员已创建'}, status=201)


class ApprovalApi(FamilyAPIView):
    permission_classes = [FamilyAdmin]

    @transaction.atomic
    def post(self, request, pk):
        profile = get_object_or_404(UserProfile.objects.select_for_update(),
                                    user_id=pk)
        profile.is_approved = True
        profile.save(update_fields=['is_approved'])
        return Response({'message': '账号已批准'})
