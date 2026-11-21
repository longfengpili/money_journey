from django.urls import path

from . import auth

urlpatterns = [
    path('auth/context/', auth.context),
    path('auth/login/', auth.sign_in),
    path('auth/logout/', auth.sign_out),
]
