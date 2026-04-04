"""
URL configuration for money_journey project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.http import JsonResponse
from django.views.generic import RedirectView
from django.views.generic import TemplateView

def health_check(request):
    """Health check endpoint for Docker and monitoring"""
    return JsonResponse({"status": "healthy", "service": "money_journey"})

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='index.html'), name='home'), # 首页路由
    path('accounts/', include('accounts.urls')),
    path('funds/', include('funds.urls')),
    path('analytics/', include('analytics.urls')),
    path('savings-calculator/', include('savings_calculator.urls')),
    # # 旧records路由重定向到新的funds路由
    # path('records/', RedirectView.as_view(pattern_name='record_list', permanent=True)),
    # path('records/add/', RedirectView.as_view(pattern_name='add_record', permanent=True)),
    # path('records/<int:record_id>/edit/', RedirectView.as_view(pattern_name='edit_record', permanent=True)),
    # path('records/upload-csv/', RedirectView.as_view(pattern_name='upload_csv', permanent=True)),
    # path('records/download-template/', RedirectView.as_view(pattern_name='download_csv_template', permanent=True)),
    # Health check endpoint
    path('health/', health_check, name='health_check'),
]
