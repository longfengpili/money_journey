from django.urls import path
from analytics.views import dashboard, charts

app_name = 'analytics'

urlpatterns = [
    path('dashboard/', dashboard, name='dashboard'),
    path('charts/', charts, name='charts'),
]