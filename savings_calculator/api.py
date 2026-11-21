"""计算 JSON 输入与会话恢复，复用共享表单及原计算引擎。"""

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import can_write_assets
from money_journey.api.base import encode_values
from savings_calculator.calculator import SavingsCalculator
from savings_calculator.forms import AgeRangeForm, BasicParametersForm
from savings_calculator.inputs import prepare_calculation_inputs


@method_decorator(csrf_protect, name="dispatch")
class CalculatorApi(APIView):
    permission_classes = [AllowAny]

    def check_account(self, request):
        if request.user.is_authenticated and not can_write_assets(
            request.user
        ):
            raise PermissionDenied()

    def get(self, request):
        self.check_account(request)
        return Response(
            request.session.get(
                "frontend_calculation",
                {
                    "results": [],
                    "summary": {},
                    "params": None,
                },
            )
        )

    def post(self, request):
        self.check_account(request)
        data = request.data
        if not isinstance(data, dict) or not isinstance(
            data.get("basic"), dict
        ):
            raise ValidationError({"basic": ["请输入基本参数"]})
        ranges = data.get("age_ranges")
        if not isinstance(ranges, list) or not 1 <= len(ranges) <= 20:
            raise ValidationError({"age_ranges": ["请设置 1 至 20 个年龄段"]})
        basic = BasicParametersForm(data["basic"])
        errors = {}
        if not basic.is_valid():
            errors.update(
                {key: list(value) for key, value in basic.errors.items()}
            )
        cleaned_ranges = []
        for index, item in enumerate(ranges):
            if not isinstance(item, dict):
                errors[f"age_ranges.{index}"] = ["年龄段格式错误"]
                continue
            form = AgeRangeForm(item)
            if not form.is_valid():
                errors.update(
                    {
                        f"age_ranges.{index}.{key}": list(value)
                        for key, value in form.errors.items()
                    }
                )
            else:
                cleaned_ranges.append(form.cleaned_data)
        if errors:
            raise ValidationError(errors)
        try:
            inputs = prepare_calculation_inputs(
                basic.cleaned_data, cleaned_ranges, user=request.user
            )
            calculator = SavingsCalculator(
                basic.cleaned_data, cleaned_ranges, **inputs
            )
            rows = calculator.calculate()
            if not rows:
                raise ValueError(
                    "没有可计算的月份，请将起始年龄设为 80 岁以下"
                )
            payload = encode_values(
                {
                    "results": rows,
                    "summary": calculator.get_summary(decimal_values=True),
                    "params": {
                        "basic": basic.cleaned_data,
                        "age_ranges": cleaned_ranges,
                    },
                }
            )
        except (ValueError, OverflowError) as exc:
            raise ValidationError({"__all__": [str(exc)]})
        request.session["frontend_calculation"] = payload
        return Response(payload)
