from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from django.contrib.auth.models import User

from funds.models import FundRecord, FundSnapshot
from .demorecord import DEMO_DATA

import logging
logger = logging.getLogger(__name__)

# def index(request):
#     """首页视图"""
#     return render(request, 'analytics/index.html')


def dashboard(request):
    """仪表板视图 - 显示汇总数据"""
    if not request.user.is_authenticated:
        # 游客模式：返回演示数据
        # 游客模式下也传递筛选参数上下文，但不对演示数据进行筛选
        context = DEMO_DATA.copy()
        context['filter_form'] = {
            'owner': '',
            'bank': '',
            'category': '',
            'savings_status': 'ACTIVE',
        }
        # 提供选择项用于表单渲染
        context['bank_choices'] = FundRecord.BANK_CHOICES
        context['category_choices'] = FundRecord.CATEGORY_CHOICES
        context['savings_status_choices'] = FundRecord.SAVINGS_STATUS_CHOICES
        context['owner_filter_choices'] = []
        return render(request, 'analytics/dashboard.html', context)

    # 登录用户：查询真实数据
    # 获取筛选参数
    owner_filter = request.GET.get('owner', '').strip()
    bank_filter = request.GET.get('bank', '').strip()
    category_filter = request.GET.get('category', '').strip()
    savings_status_filter = request.GET.get('savings_status', '').strip()
    # 检查用户是否明确选择了储蓄状态（包括空字符串，表示全部状态）
    savings_status_explicit = 'savings_status' in request.GET

    # 构建筛选条件
    filters = Q()

    # 所有者筛选：支持部分匹配
    if owner_filter:
        filters &= Q(owner__icontains=owner_filter)

    # 银行筛选：精确匹配银行代码
    if bank_filter:
        filters &= Q(bank=bank_filter)

    # 类别筛选：精确匹配类别代码
    if category_filter:
        filters &= Q(category=category_filter)

    # 储蓄状态筛选
    if savings_status_explicit:
        # 用户明确选择了储蓄状态筛选
        if savings_status_filter:
            # 非空值：应用精确匹配
            filters &= Q(savings_status=savings_status_filter)
        # 如果为空字符串，表示用户选择“全部状态”，不添加筛选条件
    else:
        # 用户未提供储蓄状态参数，默认只显示ACTIVE状态
        filters &= Q(savings_status='ACTIVE')

    # 应用筛选
    filtered_records = FundRecord.objects.filter(filters).order_by('-due_date')

    # 创建选择项映射字典
    bank_choices = dict(FundRecord.BANK_CHOICES)
    category_choices = dict(FundRecord.CATEGORY_CHOICES)
    savings_status_choices = dict(FundRecord.SAVINGS_STATUS_CHOICES)

    # 按所有者汇总（使用筛选后的记录）
    owner_summary_raw = filtered_records.values('owner').annotate(
        total_amount=Sum('amount'),
        record_count=Count('id')
    ).order_by('-total_amount')

    # 获取所有用户名的first_name映射
    usernames = [item['owner'] for item in owner_summary_raw]
    users = User.objects.filter(username__in=usernames).only('username', 'first_name')
    user_map = {}
    for user in users:
        first_name = user.first_name.strip()
        user_map[user.username] = first_name if first_name else user.username

    # 转换owner_summary，添加first_name
    owner_summary = []
    for item in owner_summary_raw:
        item_dict = dict(item)
        username = item['owner']
        item_dict['first_name'] = user_map.get(username, username)
        owner_summary.append(item_dict)

    # 按银行汇总（使用筛选后的记录）
    bank_summary_raw = filtered_records.values('bank').annotate(
        total_amount=Sum('amount'),
        record_count=Count('id')
    ).order_by('-total_amount')

    bank_summary = []
    for item in bank_summary_raw:
        item_dict = dict(item)
        item_dict['bank_display'] = bank_choices.get(item['bank'], item['bank'])
        bank_summary.append(item_dict)

    # 按类别汇总（使用筛选后的记录）
    category_summary_raw = filtered_records.values('category').annotate(
        total_amount=Sum('amount'),
        record_count=Count('id')
    ).order_by('-total_amount')

    category_summary = []
    for item in category_summary_raw:
        item_dict = dict(item)
        item_dict['category_display'] = category_choices.get(item['category'], item['category'])
        category_summary.append(item_dict)

    # 按储蓄状态汇总（使用筛选后的记录）
    status_summary_raw = filtered_records.values('savings_status').annotate(
        total_amount=Sum('amount'),
        record_count=Count('id')
    ).order_by('-total_amount')

    status_summary = []
    for item in status_summary_raw:
        item_dict = dict(item)
        item_dict['savings_status_display'] = savings_status_choices.get(item['savings_status'], item['savings_status'])
        status_summary.append(item_dict)

    # 计算总金额和记录数
    total_amount = filtered_records.aggregate(total=Sum('amount'))['total'] or 0
    total_records = filtered_records.count()
    owner_count = len(owner_summary)

    # 准备图表数据
    category_labels = [item['category_display'] for item in category_summary]
    category_totals = [float(item['total_amount']) for item in category_summary]

    bank_labels = [item['bank_display'] for item in bank_summary]
    bank_totals = [float(item['total_amount']) for item in bank_summary]

    # 获取资金快照数据（使用筛选后的记录的所有者进行过滤）
    filters_for_snapshots = Q()
    if owner_filter:
        filters_for_snapshots &= Q(owner__icontains=owner_filter)
    snapshots = FundSnapshot.objects.filter(filters_for_snapshots).values('snapshot_date').annotate(total_amount=Sum('total_amount')).order_by('snapshot_date')
    # logger.info(f"查询资金快照，筛选条件：{filters_for_snapshots}, 快照数量：{snapshots}")

    snapshot_dates = [s['snapshot_date'].strftime('%Y-%m-%d %H:%M') for s in snapshots]
    snapshot_totals = [float(s['total_amount']) for s in snapshots]

    # 获取唯一的所有者、银行、类别列表用于筛选表单
    all_owners_filter = FundRecord.objects.values_list('owner', flat=True).distinct().order_by('owner')
    # 将所有者映射到显示名称
    owner_filter_choices = []
    for owner in all_owners_filter:
        user = User.objects.filter(username=owner).first()
        display_name = user.first_name.strip() if user and user.first_name.strip() else owner
        owner_filter_choices.append((owner, display_name))

    context = {
        'owner_summary': owner_summary,
        'bank_summary': bank_summary,
        'category_summary': category_summary,
        'status_summary': status_summary,
        'total_amount': total_amount,
        'total_records': total_records,
        'owner_count': owner_count,
        'category_labels': category_labels,
        'category_totals': category_totals,
        'bank_labels': bank_labels,
        'bank_totals': bank_totals,

        # 快照数据
        'snapshot_dates': snapshot_dates,
        'snapshot_totals': snapshot_totals,
        'has_snapshots': snapshots.exists(),

        # 筛选相关上下文
        'filter_form': {
            'owner': owner_filter,
            'bank': bank_filter,
            'category': category_filter,
            'savings_status': savings_status_filter if savings_status_explicit else 'ACTIVE',
        },
        'bank_choices': FundRecord.BANK_CHOICES,
        'category_choices': FundRecord.CATEGORY_CHOICES,
        'savings_status_choices': FundRecord.SAVINGS_STATUS_CHOICES,
        'owner_filter_choices': owner_filter_choices,
    }

    return render(request, 'analytics/dashboard.html', context)


@login_required
def charts(request):
    """图表展示页面"""
    # 根据用户权限确定查询集
    # if request.user.is_superuser:
    #     records = FundRecord.objects.filter(savings_status='ACTIVE').order_by('due_date')
    # else:
    #     records = FundRecord.objects.filter(user=request.user, savings_status='ACTIVE').order_by('due_date')

    records = FundRecord.objects.filter(savings_status='ACTIVE').order_by('due_date')

    # 获取图表数据
    owner_data = records.values('owner').annotate(total=Sum('amount')).order_by('-total')
    bank_data = records.values('bank').annotate(total=Sum('amount')).order_by('-total')
    category_data = records.values('category').annotate(total=Sum('amount')).order_by('-total')

    # 创建银行选择项映射字典
    bank_choices = dict(FundRecord.BANK_CHOICES)
    category_choices = dict(FundRecord.CATEGORY_CHOICES)

    # 获取所有用户名的first_name映射
    usernames = [item['owner'] for item in owner_data]
    users = User.objects.filter(username__in=usernames).only('username', 'first_name')
    user_map = {}
    for user in users:
        # 如果first_name为空或只包含空格，使用username
        first_name = user.first_name.strip()
        user_map[user.username] = first_name if first_name else user.username

    # 转换数据格式便于Chart.js使用
    owner_labels = [user_map.get(item['owner'], item['owner']) for item in owner_data]
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
    return render(request, 'analytics/charts.html', context)