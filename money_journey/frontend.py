"""组件化前端入口与旧页面兼容。"""

from django.conf import settings
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.views.decorators.cache import never_cache


@never_cache
def home(request):
    return retired_page(request, target="/app/")


def retired_page(request, target, **kwargs):
    """保留旧书签，但不再执行旧表单写入。"""
    if request.method not in ("GET", "HEAD"):
        return JsonResponse(
            {
                "code": "LEGACY_ENDPOINT_RETIRED",
                "message": "旧页面提交入口已停用，请在新页面重新操作。",
                "url": target,
            },
            status=410,
        )
    query = request.GET.urlencode()
    return redirect(target + ("?" + query if query else ""))


@never_cache
def app_index(request, route=""):
    index = settings.FRONTEND_DIST / "index.html"
    if not index.is_file():
        return HttpResponse(
            "前端尚未构建，请运行 frontend 中的 npm run build", status=503
        )
    return FileResponse(index.open("rb"), content_type="text/html")
