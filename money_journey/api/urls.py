from django.urls import path

from . import auth
from analytics.api import SummaryApi, TrendApi
from funds.api import FundDetailApi, FundOptionsApi, FundsApi
from funds.operation_api import ImportApi, ImportTemplateApi, SnapshotRefreshApi
from savings_calculator.api import CalculatorApi

urlpatterns = [
    path('calculator/calculate/', CalculatorApi.as_view()),
    path('calculator/result/', CalculatorApi.as_view()),
    path('funds/import/', ImportApi.as_view()),
    path('funds/import-template/', ImportTemplateApi.as_view()),
    path('snapshots/refresh/', SnapshotRefreshApi.as_view()),
    path('funds/options/', FundOptionsApi.as_view()),
    path('funds/', FundsApi.as_view()),
    path('funds/<int:pk>/', FundDetailApi.as_view()),
    path('analytics/summary/', SummaryApi.as_view()),
    path('analytics/trend/', TrendApi.as_view()),
    path('auth/context/', auth.context),
    path('auth/login/', auth.sign_in),
    path('auth/logout/', auth.sign_out),
]
