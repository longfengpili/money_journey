from django.urls import path
from django.contrib.auth import views as auth_views
from accounts.views import (
    CustomLoginView, approve_user, create_member, register, user_approval_list,
)

app_name = 'accounts'

urlpatterns = [
    path('members/create/', create_member, name='create_member'),
    path('login/', CustomLoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', register, name='register'),
    path('approval/', user_approval_list, name='user_approval_list'),
    path('approve/<int:user_id>/', approve_user, name='approve_user'),
]
