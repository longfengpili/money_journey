from django import forms
from django.contrib.auth.models import User


class CreateMemberForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('username', 'first_name')
        labels = {'username': '用户名', 'first_name': '姓名'}
