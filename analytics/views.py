from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from django.contrib.auth.models import User

from funds.models import FundRecord, FundSnapshot


def index(request):
    """首页视图"""
    return render(request, 'analytics/index.html')


@login_required
def dashboard(request):
    """仪表板视图 - 显示汇总数据"""
    # 创建选择项映射字典
    bank_choices = dict(FundRecord.BANK_CHOICES)
    category_choices = dict(FundRecord.CATEGORY_CHOICES)
    savings_status_choices = dict(FundRecord.SAVINGS_STATUS_CHOICES)

    # 根据用户权限确定查询集
    # if request.user.is_superuser:
    #     active_records = FundRecord.objects.filter(savings_status='ACTIVE').order_by('-due_date')
    #     all_records = FundRecord.objects.all()
    # else:
    #     active_records = FundRecord.objects.filter(user=request.user, savings_status='ACTIVE').order_by('-due_date')
    #     all_records = FundRecord.objects.filter(user=request.user)

    active_records = FundRecord.objects.filter(savings_status='ACTIVE').order_by('-due_date')
    all_records = FundRecord.objects.all()

    # 按所有者汇总（使用ACTIVE记录）
    owner_summary_raw = active_records.values('owner').annotate(
        total_amount=Sum('amount'),
        record_count=Count('id')
    ).order_by('-total_amount')

    # 获取所有用户名的first_name映射
    usernames = [item['owner'] for item in owner_summary_raw]
    users = User.objects.filter(username__in=usernames).only('username', 'first_name')
    user_map = {}
    for user in users:
        # 如果first_name为空或只包含空格，使用username
        first_name = user.first_name.strip()
        user_map[user.username] = first_name if first_name else user.username

    # 转换owner_summary，添加first_name
    owner_summary = []
    for item in owner_summary_raw:
        item_dict = dict(item)
        username = item['owner']
        item_dict['first_name'] = user_map.get(username, username)  # 如果没有first_name，显示用户名
        owner_summary.append(item_dict)

    # 按银行汇总（使用ACTIVE记录）
    bank_summary_raw = active_records.values('bank').annotate(
        total_amount=Sum('amount'),
        record_count=Count('id')
    ).order_by('-total_amount')

    # 转换银行汇总数据，添加显示标签
    bank_summary = []
    for item in bank_summary_raw:
        item_dict = dict(item)
        item_dict['bank_display'] = bank_choices.get(item['bank'], item['bank'])
        bank_summary.append(item_dict)

    # 按类别汇总（使用ACTIVE记录）
    category_summary_raw = active_records.values('category').annotate(
        total_amount=Sum('amount'),
        record_count=Count('id')
    ).order_by('-total_amount')

    # 转换类别汇总数据，添加显示标签
    category_summary = []
    for item in category_summary_raw:
        item_dict = dict(item)
        item_dict['category_display'] = category_choices.get(item['category'], item['category'])
        category_summary.append(item_dict)

    # 按储蓄状态汇总（使用所有记录）
    status_summary_raw = active_records.values('savings_status').annotate(
        total_amount=Sum('amount'),
        record_count=Count('id')
    ).order_by('-total_amount')

    # 转换储蓄状态汇总数据，添加显示标签
    status_summary = []
    for item in status_summary_raw:
        item_dict = dict(item)
        item_dict['savings_status_display'] = savings_status_choices.get(item['savings_status'], item['savings_status'])
        status_summary.append(item_dict)

    # 计算总金额和记录数
    total_amount = active_records.aggregate(total=Sum('amount'))['total'] or 0
    total_records = active_records.count()
    owner_count = len(owner_summary)

    # 准备图表数据
    category_labels = [item['category_display'] for item in category_summary]
    category_totals = [float(item['total_amount']) for item in category_summary]

    bank_labels = [item['bank_display'] for item in bank_summary]
    bank_totals = [float(item['total_amount']) for item in bank_summary]

    # 新增：获取快照历史数据
    snapshots = FundSnapshot.objects.all().order_by('snapshot_date')

    snapshot_dates = [s.snapshot_date.strftime('%Y-%m-%d %H:%M') for s in snapshots]
    snapshot_totals = [float(s.total_amount) for s in snapshots]

    # 获取所有所有者列表（用于下拉菜单）
    all_owners = list(set([owner for snapshot in snapshots for owner in snapshot.owner_summary.keys()]))
    owner_display_names = [user_map.get(owner, owner) for owner in all_owners]
    owner_choices = list(zip(all_owners, owner_display_names))

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
        'owner_choices': owner_choices,
        'has_snapshots': snapshots.exists(),
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