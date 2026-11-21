"""家庭资产统计页面，查询规则由统一模块提供。"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from funds.models import FundRecord

from .demorecord import DEMO_DATA
from .queries import (
    get_owner_choices,
    get_snapshot_trend,
    normalize_filters,
    summarize_assets,
)


def _chart_data(summary, snapshots=()):
    """仅在图表展示边界将金额转换为浏览器数值。"""
    data = {}
    for dimension, label in (
        ('owner', 'first_name'),
        ('bank', 'bank_display'),
        ('category', 'category_display'),
    ):
        rows = summary[dimension + '_summary']
        data[dimension + '_labels'] = [row[label] for row in rows]
        data[dimension + '_totals'] = [
            float(row['total_amount']) for row in rows
        ]
    data['snapshot_dates'] = [
        row['snapshot_date'].strftime('%Y-%m-%d') for row in snapshots
    ]
    data['snapshot_totals'] = [float(row['total_amount']) for row in snapshots]
    return data


def dashboard(request):
    """实时汇总跟随全部筛选，历史 ACTIVE 趋势只跟随所有者。"""
    if request.user.is_authenticated:
        filters = normalize_filters(request.GET)
        context = summarize_assets(filters)
        snapshots = get_snapshot_trend(filters['owner'])
        context.update(_chart_data(context, snapshots))
        context['has_snapshots'] = bool(snapshots)
        context['owner_filter_choices'] = get_owner_choices()
    else:
        # 游客继续展示既有演示数据，图表同样通过 JSON 传递。
        context = DEMO_DATA.copy()
        filters = normalize_filters({})
        context.update(_chart_data(context))
        context['owner_filter_choices'] = []
    selected_labels = [
        label for owner, label in context['owner_filter_choices']
        if owner == filters['owner']
    ]
    context['selected_owner_label'] = (
        selected_labels[0] if len(selected_labels) == 1 else filters['owner']
    )
    if filters['owner'] and not selected_labels:
        # 部分用户名及仅剩历史快照的账号也须保留当前筛选值。
        context['owner_filter_choices'].insert(
            0, (filters['owner'], filters['owner'])
        )
    context.update({
        'filter_form': filters,
        'bank_choices': FundRecord.BANK_CHOICES,
        'category_choices': FundRecord.CATEGORY_CHOICES,
        'savings_status_choices': FundRecord.SAVINGS_STATUS_CHOICES,
    })
    context['chart_data'] = {
        key: context[key]
        for key in (
            'owner_labels', 'owner_totals', 'bank_labels', 'bank_totals',
            'category_labels', 'category_totals',
            'snapshot_dates', 'snapshot_totals',
        )
    }
    return render(request, 'analytics/dashboard.html', context)


@login_required
def charts(request):
    """共享全家 ACTIVE 分布，复用仪表板统计规则。"""
    data = _chart_data(summarize_assets())
    return render(
        request, 'analytics/charts.html', {**data, 'chart_data': data}
    )
