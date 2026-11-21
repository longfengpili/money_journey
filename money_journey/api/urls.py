from django.urls import path

from . import auth
from analytics.api import SummaryApi, TrendApi

urlpatterns = [
    path('analytics/summary/', SummaryApi.as_view()),
    path('analytics/trend/', TrendApi.as_view()),
    path('auth/context/', auth.context),
    path('auth/login/', auth.sign_in),
    path('auth/logout/', auth.sign_out),
]
