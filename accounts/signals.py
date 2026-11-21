"""任何登录入口切换身份时清理原会话的计算结果。"""

from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver


@receiver(
    user_logged_in, dispatch_uid="money_journey.clear_calculation_session"
)
def clear_calculation_session(sender, request, **kwargs):
    if request is not None:
        for key in (
            "frontend_calculation",
            "calculation_results",
            "calculation_summary",
            "calculation_params",
        ):
            request.session.pop(key, None)
