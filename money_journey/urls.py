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
from django.urls import path, include, re_path
from money_journey.frontend import app_index, home
from django.http import JsonResponse


def health_check(request):
    """Health check endpoint for Docker and monitoring"""
    return JsonResponse({"status": "healthy", "service": "money_journey"})


urlpatterns = [
    path("api/v1/", include("money_journey.api.urls")),
    path("app/", app_index, name="frontend"),
    re_path(r"^app/(?P<route>.*)$", app_index),
    path("admin/", admin.site.urls),
    path("", home, name="index"),
    path("legacy/", home, name="legacy"),
    path("accounts/", include("accounts.urls")),
    path("funds/", include("funds.urls")),
    path("analytics/", include("analytics.urls")),
    path("savings-calculator/", include("savings_calculator.urls")),
    path("health/", health_check, name="health_check"),
]
