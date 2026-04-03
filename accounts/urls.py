from django.urls import path
from django.contrib.auth import views as auth_views
from accounts.views import CustomLoginView, register, user_approval_list, approve_user

app_name = 'accounts'

urlpatterns = [
    path('login/', CustomLoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', register, name='register'),
    path('approval/', user_approval_list, name='user_approval_list'),
    path('approve/<int:user_id>/', approve_user, name='approve_user'),
]