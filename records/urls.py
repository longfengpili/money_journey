from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('records/', views.record_list, name='record_list'),
    path('charts/', views.charts, name='charts'),
]