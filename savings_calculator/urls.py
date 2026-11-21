from django.urls import path
from . import views

app_name = "savings_calculator"

urlpatterns = [
    # 游客模式路由
    path("", views.calculator_input, name="calculator_input"),
    path("calculate/", views.calculate, name="calculate"),
    path("results/", views.results, name="results"),
]
