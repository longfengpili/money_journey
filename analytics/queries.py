"""家庭资产筛选、统一汇总及每日快照趋势查询。"""

from decimal import Decimal

from django.db.models import Case, CharField, Count, F, Q, Sum, Value, When

from funds.models import FundRecord, FundSnapshot


def normalize_filters(params):
    """保留缺失状态与显式全部状态的区别。"""
    return {
        'owner': params.get('owner', '').strip(),
        'bank': params.get('bank', '').strip(),
        'category': params.get('category', '').strip(),
        'savings_status': params.get('savings_status', 'ACTIVE').strip(),
    }


def _owner_filter(owner):
    return (
        Q(user__username__icontains=owner)
        | Q(user__isnull=True, owner__icontains=owner)
    )


def _accumulate(rows, key, initial, amount, count):
    row = rows.setdefault(key, {
        **initial, 'total_amount': Decimal('0'), 'record_count': 0,
    })
    row['total_amount'] += amount
    row['record_count'] += count


def summarize_assets(filters=None):
    """一次分组查询生成总计及四个维度，金额始终使用 Decimal。"""
    filters = normalize_filters(filters if filters is not None else {})
    records = FundRecord.objects.all()
    if filters['owner']:
        records = records.filter(_owner_filter(filters['owner']))
    for field in ('bank', 'category', 'savings_status'):
        if filters[field]:
            records = records.filter(**{field: filters[field]})
    groups = records.order_by().values(
        'user_id', 'bank', 'category', 'savings_status',
        account_username=F('user__username'),
        account_name=F('user__first_name'),
        legacy_owner=Case(
            When(user__isnull=True, then=F('owner')),
            default=Value(''), output_field=CharField(),
        ),
    ).annotate(total_amount=Sum('amount'), record_count=Count('pk'))
    owners = {}
    dimensions = {
        field: {} for field in ('bank', 'category', 'savings_status')
    }
    choices = {
        'bank': dict(FundRecord.BANK_CHOICES),
        'category': dict(FundRecord.CATEGORY_CHOICES),
        'savings_status': dict(FundRecord.SAVINGS_STATUS_CHOICES),
    }
    total_amount, total_records = Decimal('0'), 0
    for group in groups:
        amount, count = group['total_amount'], group['record_count']
        total_amount += amount
        total_records += count
        owner = group['account_username'] or group['legacy_owner']
        name = (group['account_name'] or '').strip() or owner or '待核对所有者'
        _accumulate(
            owners, (group['user_id'], group['legacy_owner']),
            {'user_id': group['user_id'], 'owner': owner, 'first_name': name},
            amount, count,
        )
        for field, rows in dimensions.items():
            code = group[field]
            _accumulate(rows, code, {
                field: code,
                field + '_display': choices[field].get(code, code),
            }, amount, count)

    result = {
        'total_amount': total_amount,
        'total_records': total_records,
        'owner_count': len(owners),
        'owner_summary': sorted(owners.values(), key=lambda row: (
            -row['total_amount'], row['user_id'] is None,
            row['user_id'] or 0, row['owner'] or '',
        )),
    }
    for field, rows in dimensions.items():
        name = 'status' if field == 'savings_status' else field
        result[name + '_summary'] = sorted(
            rows.values(), key=lambda row: (-row['total_amount'], row[field]),
        )
    return result


def get_owner_choices():
    """筛选选项覆盖全家所有状态，沿用金额降序。"""
    return [
        (row['owner'], row['first_name'])
        for row in summarize_assets({'savings_status': ''})['owner_summary']
    ]


def get_snapshot_trend(owner=''):
    """关联账号按当前用户名筛选，空关联历史只使用原名称。"""
    snapshots = FundSnapshot.objects.all()
    owner = owner.strip()
    if owner:
        snapshots = snapshots.filter(_owner_filter(owner))
    return list(
        snapshots.order_by().values('snapshot_date')
        .annotate(total_amount=Sum('total_amount')).order_by('snapshot_date')
    )
