from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm


class RegistrationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        fields = ('username', 'first_name', 'email')


class CreateMemberForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('username', 'first_name')
        labels = {'username': '用户名', 'first_name': '姓名'}
