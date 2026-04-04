from django.urls import path
from . import views

app_name = "savings_calculator"

urlpatterns = [
    # 游客模式路由
    path('', views.CalculatorInputView.as_view(), name='calculator_input'),
    path('calculate/', views.CalculateView.as_view(), name='calculate'),
    path('results/', views.ResultsView.as_view(), name='results'),

    # 登录模式路由
    path('loggedin/', views.LoggedInCalculatorInputView.as_view(), name='calculator_input_loggedin'),
    path('loggedin/calculate/', views.LoggedInCalculateView.as_view(), name='calculate_loggedin'),
    path('loggedin/results/', views.LoggedInResultsView.as_view(), name='results_loggedin'),
]