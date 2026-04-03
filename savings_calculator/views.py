# 剩余资金计算视图
from django.shortcuts import render, redirect
from django.views.generic import View, TemplateView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib import messages
from .forms import BasicParametersForm, create_age_range_formset
from .calculator import SavingsCalculator
from decimal import Decimal
import json


def convert_decimals_to_floats(obj):
    """递归地将对象中的Decimal值转换为float，以便JSON序列化"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {key: convert_decimals_to_floats(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals_to_floats(item) for item in obj]
    else:
        return obj


@method_decorator(login_required, name='dispatch')
class CalculatorInputView(TemplateView):
    """参数输入页面"""
    template_name = 'savings_calculator/calculator_input.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 创建表单实例
        context['basic_form'] = BasicParametersForm()
        AgeRangeFormSet = create_age_range_formset()
        context['age_range_formset'] = AgeRangeFormSet()

        # 添加默认年龄段（25-35岁，收入10000，支出5000）
        default_data = {
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '0',
            'form-MIN_NUM_FORMS': '1',
            'form-MAX_NUM_FORMS': '20',
            'form-0-start_age': '25',
            'form-0-end_age': '35',
            'form-0-monthly_income': '10000',
            'form-0-monthly_expense': '5000',
        }
        context['age_range_formset'] = AgeRangeFormSet(default_data)

        return context


@method_decorator(login_required, name='dispatch')
class CalculateView(View):
    """处理计算请求"""

    def post(self, request):
        # 处理基本参数表单
        basic_form = BasicParametersForm(request.POST)
        AgeRangeFormSet = create_age_range_formset()
        age_range_formset = AgeRangeFormSet(request.POST)

        if not basic_form.is_valid():
            messages.error(request, '基本参数表单有误，请检查输入')
            return render(request, 'savings_calculator/calculator_input.html', {
                'basic_form': basic_form,
                'age_range_formset': age_range_formset,
            })

        if not age_range_formset.is_valid():
            messages.error(request, '年龄段参数有误，请检查输入')
            return render(request, 'savings_calculator/calculator_input.html', {
                'basic_form': basic_form,
                'age_range_formset': age_range_formset,
            })

        try:
            # 提取基本参数
            basic_params = {
                'parent_birth_year': basic_form.cleaned_data['parent_birth_year'],
                'child_birth_year': basic_form.cleaned_data['child_birth_year'],
                'current_amount': basic_form.cleaned_data['current_amount'],
                'three_year_rate': basic_form.cleaned_data['three_year_rate'],
                'extra_budget': basic_form.cleaned_data['extra_budget'],
                'annual_expense': basic_form.cleaned_data['annual_expense'],
                'annual_expense_month': basic_form.cleaned_data['annual_expense_month'],
                'calculation_months': basic_form.cleaned_data['calculation_months'],
            }

            # 提取年龄段参数
            age_range_params = []
            for form in age_range_formset:
                if form.cleaned_data:  # 跳过空表单
                    age_range_params.append({
                        'start_age': form.cleaned_data['start_age'],
                        'end_age': form.cleaned_data['end_age'],
                        'monthly_income': form.cleaned_data['monthly_income'],
                        'monthly_expense': form.cleaned_data['monthly_expense'],
                    })

            if not age_range_params:
                messages.error(request, '至少需要设置一个年龄段')
                return render(request, 'savings_calculator/calculator_input.html', {
                    'basic_form': basic_form,
                    'age_range_formset': age_range_formset,
                })

            # 创建计算器并执行计算
            calculator = SavingsCalculator(basic_params, age_range_params)
            results = calculator.calculate()
            summary = calculator.get_summary()

            # 将结果存储到session中（仅实时计算，不持久化）
            request.session['calculation_results'] = [
                {
                    'month': r['month'],
                    'month_index': r['month_index'],
                    'age': r['age'],
                    'child_age': r['child_age'],
                    'total': float(r['total']),
                    'regular_accumulated': float(r['regular_accumulated']),
                    'regular_transfer': float(r['regular_transfer']),
                    'current_deposit_before_expense': float(r['current_deposit_before_expense']),
                    'regular_deposit_standard': float(r['regular_deposit_standard']),
                    'regular_deposit': float(r['regular_deposit']),
                    'income': float(r['income']),
                    'total_expense': float(r['total_expense']),
                    'expense': float(r['expense']),
                    'extra_budget': float(r['extra_budget']),
                    'is_annual_expense_month': r['is_annual_expense_month'],
                }
                for r in results
            ]

            # 转换summary和params中的Decimal为float，以便JSON序列化
            request.session['calculation_summary'] = convert_decimals_to_floats(summary)
            request.session['calculation_params'] = convert_decimals_to_floats({
                'basic': basic_params,
                'age_ranges': age_range_params,
            })

            # 重定向到结果页面
            return redirect('savings_calculator:results')

        except ValueError as e:
            messages.error(request, f'计算错误：{str(e)}')
            return render(request, 'savings_calculator/calculator_input.html', {
                'basic_form': basic_form,
                'age_range_formset': age_range_formset,
            })
        except Exception as e:
            messages.error(request, f'系统错误：{str(e)}')
            return render(request, 'savings_calculator/calculator_input.html', {
                'basic_form': basic_form,
                'age_range_formset': age_range_formset,
            })


@method_decorator(login_required, name='dispatch')
class ResultsView(TemplateView):
    """计算结果展示页面"""
    template_name = 'savings_calculator/calculator_results.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 从session获取结果
        results = self.request.session.get('calculation_results')
        summary = self.request.session.get('calculation_summary')
        params = self.request.session.get('calculation_params')

        if not results:
            messages.warning(self.request, '没有找到计算结果，请先进行计算')
            return redirect('savings_calculator:calculator_input')

        context['results'] = results
        context['summary'] = summary
        context['params'] = params
        context['results_json'] = json.dumps(results, ensure_ascii=False)

        return context