from django.urls import path

from . import auth
from analytics.api import SummaryApi, TrendApi
from funds.api import FundDetailApi, FundOptionsApi, FundsApi

urlpatterns = [
    path('funds/options/', FundOptionsApi.as_view()),
    path('funds/', FundsApi.as_view()),
    path('funds/<int:pk>/', FundDetailApi.as_view()),
    path('analytics/summary/', SummaryApi.as_view()),
    path('analytics/trend/', TrendApi.as_view()),
    path('auth/context/', auth.context),
    path('auth/login/', auth.sign_in),
    path('auth/logout/', auth.sign_out),
]
