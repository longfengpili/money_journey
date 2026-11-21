from django.urls import path
from accounts.views import (
    login,
    logout,
    approve_user,
    create_member,
    register,
    user_approval_list,
)

app_name = "accounts"

urlpatterns = [
    path("members/create/", create_member, name="create_member"),
    path("login/", login, name="login"),
    path("logout/", logout, name="logout"),
    path("register/", register, name="register"),
    path("approval/", user_approval_list, name="user_approval_list"),
    path("approve/<int:user_id>/", approve_user, name="approve_user"),
]
