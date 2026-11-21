"""从家庭资产和表单准备计算输入，集中处理数据库与当前日期。"""

from datetime import date
from decimal import Decimal

from django.db.models import F, Q, Sum
from django.utils import timezone

from funds.models import FundRecord


def prepare_calculation_inputs(
    basic_params,
    age_range_params,
    *,
    user,
    today=None,
):
    if not age_range_params:
        raise ValueError('至少需要设置一个年龄段')
    if not user.is_authenticated:
        start_age = min(item['start_age'] for item in age_range_params)
        return {
            'start_date': date(
                basic_params['parent_birth_year'] + start_age, 1, 1
            ),
            'initial_current_amount': basic_params['current_amount'],
            'initial_deposits': [],
        }

    current_date = today if today is not None else timezone.localdate()
    funds = (
        FundRecord.objects.filter(savings_status='ACTIVE')
        .values(
            'start_date',
            'due_date',
        )
        .annotate(
            amount_sum=Sum('amount'),
            maturity_amount=Sum(
                F('amount')
                * (1 + F('interest_rate') / 100 * F('deposit_period')),
            ),
            current_amount=Sum('amount', filter=Q(category='CURRENT')),
        )
        .order_by('start_date')
    )
    current_amount = Decimal('0')
    deposits = []
    for fund in funds:
        current_amount += fund['current_amount'] or Decimal('0')
        if (
            fund['due_date'] is not None
            and fund['amount_sum'] is not None
            and fund['maturity_amount'] is not None
        ):
            deposits.append(
                (
                    fund['start_date'],
                    fund['due_date'],
                    fund['amount_sum'],
                    fund['maturity_amount'],
                )
            )
    return {
        'start_date': date(current_date.year, current_date.month, 1),
        'initial_current_amount': current_amount,
        'initial_deposits': deposits,
    }
