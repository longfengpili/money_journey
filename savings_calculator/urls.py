from django.urls import path
from . import views

app_name = "savings_calculator"

urlpatterns = [
    # 游客模式路由
    path('', views.CalculatorInputView.as_view(), name='calculator_input'),
    path('calculate/', views.CalculateView.as_view(), name='calculate'),
    path('results/', views.ResultsView.as_view(), name='results'),
]