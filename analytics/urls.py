from django.urls import path
from analytics.views import index, dashboard, charts

app_name = 'analytics'

urlpatterns = [
    path('', index, name='index'),
    path('dashboard/', dashboard, name='dashboard'),
    path('charts/', charts, name='charts'),
]