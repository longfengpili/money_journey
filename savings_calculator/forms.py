# 剩余资金计算表单定义
from django import forms
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal


class BasicParametersForm(forms.Form):
    """基本参数表单"""
    parent_birth_year = forms.IntegerField(
        label='家长出生年份',
        min_value=1900,
        max_value=2026,
        initial=1987,
        help_text='请输入家长的出生年份（1900-2026）'
    )

    child_birth_year = forms.IntegerField(
        label='孩子出生年份',
        min_value=1900,
        max_value=2026,
        initial=2014,
        help_text='请输入孩子的出生年份（1900-2026）'
    )

    current_amount = forms.DecimalField(
        label='活期金额（元）',
        max_digits=15,
        decimal_places=2,
        min_value=Decimal('0'),
        initial=Decimal('50000.00'),
        help_text='初始活期金额，假设当前已经有的资金（元）'
    )


    keep_amount = forms.DecimalField(
        label='活期持有金额（元）',
        max_digits=15,
        decimal_places=2,
        min_value=Decimal('0'),
        initial=Decimal('50000.00'),
        help_text='每月保留的活期金额，其余部分用于定期存款'
    )

    three_year_rate = forms.DecimalField(
        label='3年定期存款利率（%）',
        max_digits=5,
        decimal_places=2,
        min_value=Decimal('0'),
        max_value=Decimal('100'),
        initial=Decimal('1.60'),
        help_text='3年定期存款的年化利率（百分比）'
    )

    annual_expense = forms.DecimalField(
        label='年度支出（元/年）',
        max_digits=15,
        decimal_places=2,
        min_value=Decimal('0'),
        initial=Decimal('10000.00'),
        help_text='每年一次性的大额支出'
    )

    annual_expense_month = forms.IntegerField(
        label='年度支出扣除月份',
        min_value=1,
        max_value=12,
        initial=12,
        help_text='年度支出在哪个月份扣除（1-12）'
    )

    calculation_months = forms.IntegerField(
        label='计算月数',
        min_value=1,
        max_value=600,
        initial=360,
        help_text='需要计算的月份数量（默认360个月，即30年）'
    )


class AgeRangeForm(forms.Form):
    """年龄段参数表单"""
    start_age = forms.IntegerField(
        label='起始年龄',
        min_value=0,
        max_value=150,
        help_text='年龄段的起始年龄'
    )

    end_age = forms.IntegerField(
        label='结束年龄',
        min_value=0,
        max_value=150,
        help_text='年龄段的结束年龄（包含）'
    )

    monthly_income = forms.DecimalField(
        label='月收入（元）',
        max_digits=15,
        decimal_places=2,
        min_value=Decimal('0'),
        help_text='该年龄段的月收入'
    )

    monthly_expense = forms.DecimalField(
        label='月支出（元）',
        max_digits=15,
        decimal_places=2,
        min_value=Decimal('0'),
        help_text='该年龄段的月支出'
    )


# 创建表单集工厂函数
def create_age_range_formset(extra=1, max_num=20):
    """创建年龄段参数表单集"""
    from django.forms import formset_factory
    return formset_factory(
        AgeRangeForm,
        extra=extra,
        max_num=max_num,
        validate_min=True,
        min_num=1,
        can_delete=True
    )