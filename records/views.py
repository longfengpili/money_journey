from django.shortcuts import render
from django.db.models import Sum, Count
from django.contrib.auth.decorators import login_required
from .models import FundRecord

def index(request):
    """首页视图"""
    return render(request, 'records/index.html')

@login_required
def dashboard(request):
    """仪表板视图 - 显示汇总数据"""
    # 创建选择项映射字典
    bank_choices = dict(FundRecord.BANK_CHOICES)
    category_choices = dict(FundRecord.CATEGORY_CHOICES)
    savings_status_choices = dict(FundRecord.SAVINGS_STATUS_CHOICES)

    # 按所有者汇总
    owner_summary = FundRecord.objects.values('owner').annotate(
        total_amount=Sum('amount'),
        record_count=Count('id')
    ).order_by('-total_amount')

    # 按银行汇总
    bank_summary_raw = FundRecord.objects.values('bank').annotate(
        total_amount=Sum('amount'),
        record_count=Count('id')
    ).order_by('-total_amount')

    # 转换银行汇总数据，添加显示标签
    bank_summary = []
    for item in bank_summary_raw:
        item_dict = dict(item)
        item_dict['bank_display'] = bank_choices.get(item['bank'], item['bank'])
        bank_summary.append(item_dict)

    # 按类别汇总
    category_summary_raw = FundRecord.objects.values('category').annotate(
        total_amount=Sum('amount'),
        record_count=Count('id')
    ).order_by('-total_amount')

    # 转换类别汇总数据，添加显示标签
    category_summary = []
    for item in category_summary_raw:
        item_dict = dict(item)
        item_dict['category_display'] = category_choices.get(item['category'], item['category'])
        category_summary.append(item_dict)

    # 按储蓄状态汇总
    status_summary_raw = FundRecord.objects.values('savings_status').annotate(
        total_amount=Sum('amount'),
        record_count=Count('id')
    )

    # 转换储蓄状态汇总数据，添加显示标签
    status_summary = []
    for item in status_summary_raw:
        item_dict = dict(item)
        item_dict['savings_status_display'] = savings_status_choices.get(item['savings_status'], item['savings_status'])
        status_summary.append(item_dict)

    # 总金额
    total_amount = FundRecord.objects.aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'owner_summary': owner_summary,
        'bank_summary': bank_summary,
        'category_summary': category_summary,
        'status_summary': status_summary,
        'total_amount': total_amount,
    }
    return render(request, 'records/dashboard.html', context)

@login_required
def record_list(request):
    """资金记录列表"""
    records = FundRecord.objects.all().order_by('-created_at')
    return render(request, 'records/record_list.html', {'records': records})

@login_required
def charts(request):
    """图表展示页面"""
    # 获取图表数据
    owner_data = FundRecord.objects.values('owner').annotate(total=Sum('amount')).order_by('-total')
    bank_data = FundRecord.objects.values('bank').annotate(total=Sum('amount')).order_by('-total')
    category_data = FundRecord.objects.values('category').annotate(total=Sum('amount')).order_by('-total')

    # 创建银行选择项映射字典
    bank_choices = dict(FundRecord.BANK_CHOICES)
    category_choices = dict(FundRecord.CATEGORY_CHOICES)

    # 转换数据格式便于Chart.js使用
    owner_labels = [item['owner'] for item in owner_data]
    owner_totals = [float(item['total']) for item in owner_data]

    bank_labels = [bank_choices.get(item['bank'], item['bank']) for item in bank_data]
    bank_totals = [float(item['total']) for item in bank_data]

    category_labels = [category_choices.get(item['category'], item['category']) for item in category_data]
    category_totals = [float(item['total']) for item in category_data]

    context = {
        'owner_labels': owner_labels,
        'owner_totals': owner_totals,
        'bank_labels': bank_labels,
        'bank_totals': bank_totals,
        'category_labels': category_labels,
        'category_totals': category_totals,
    }
    return render(request, 'records/charts.html', context)