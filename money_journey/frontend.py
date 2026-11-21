"""组件化前端入口与旧页面兼容。"""

from django.conf import settings
from django.http import FileResponse, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache


@never_cache
def home(request):
    if settings.FRONTEND_ENABLED:
        return redirect("/app/")
    return render(request, "index.html")


@never_cache
def app_index(request, route=""):
    index = settings.FRONTEND_DIST / "index.html"
    if not index.is_file():
        return HttpResponse(
            "前端尚未构建，请运行 frontend 中的 npm run build", status=503
        )
    return FileResponse(index.open("rb"), content_type="text/html")
