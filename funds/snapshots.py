"""当天家庭资产快照的统一事务入口。"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Count, Sum
from django.utils import timezone

from accounts.permissions import is_family_admin
from funds.models import FundRecord, FundSnapshot


@dataclass(frozen=True)
class SnapshotRefreshResult:
    snapshot_date: date
    created_count: int
    updated_count: int


@transaction.atomic
def refresh_daily_snapshots(actor, *, snapshot_date=None):
    if not is_family_admin(actor):
        raise PermissionDenied('只有家庭管理员可以刷新家庭快照')
    day = snapshot_date if snapshot_date is not None else timezone.localdate()
    # 即使当天尚无快照，也可利用固定顺序的成员锁串行化并发刷新。
    users = list(
        User.objects.select_for_update().order_by('pk').only('pk', 'username')
    )
    user_ids = {user.pk for user in users}
    if actor.pk not in user_ids:
        raise PermissionDenied('账号状态已变化，请重新登录')
    if FundSnapshot.objects.filter(
        snapshot_date=day, user__isnull=True
    ).exists():
        raise ValidationError('当天旧快照存在未关联账号的记录，请先核对归属')
    existing = {
        snapshot.user_id: snapshot
        for snapshot in FundSnapshot.objects.select_for_update().filter(
            snapshot_date=day
        )
    }
    summaries = {
        user.pk: {
            'total_amount': Decimal('0'),
            'record_count': 0,
            'bank_summary': {},
            'category_summary': {},
        }
        for user in users
    }
    groups = (
        FundRecord.objects.filter(savings_status='ACTIVE')
        .values(
            'user_id',
            'bank',
            'category',
        )
        .annotate(total_amount=Sum('amount'), record_count=Count('pk'))
        .order_by()
    )
    for group in groups:
        user_id = group['user_id']
        if user_id is None:
            raise ValidationError('存在未关联账号的存续资产，请先核对归属')
        if user_id not in user_ids:
            raise ValidationError('家庭成员发生变化，请重试刷新')
        summary = summaries[user_id]
        amount = group['total_amount'] or Decimal('0')
        summary['total_amount'] += amount
        summary['record_count'] += group['record_count']
        for field, key in (
            ('bank_summary', 'bank'),
            ('category_summary', 'category'),
        ):
            values = summary[field]
            values[group[key]] = values.get(group[key], Decimal('0')) + amount

    new_rows, updated_rows = [], []
    now = timezone.now()
    for user in users:
        summary = summaries[user.pk]
        snapshot = existing.get(user.pk)
        if snapshot is None:
            snapshot = FundSnapshot(user=user, snapshot_date=day)
            new_rows.append(snapshot)
        else:
            updated_rows.append(snapshot)
        snapshot.owner = user.username
        snapshot.created_by = actor
        snapshot.total_amount = summary['total_amount']
        snapshot.record_count = summary['record_count']
        snapshot.bank_summary = {
            key: format(value, '.2f')
            for key, value in summary['bank_summary'].items()
        }
        snapshot.category_summary = {
            key: format(value, '.2f')
            for key, value in summary['category_summary'].items()
        }
        snapshot.updated_at = now

    FundSnapshot.objects.bulk_update(
        updated_rows,
        fields=(
            'owner',
            'created_by',
            'total_amount',
            'record_count',
            'bank_summary',
            'category_summary',
            'updated_at',
        ),
        batch_size=100,
    )
    FundSnapshot.objects.bulk_create(new_rows, batch_size=100)
    return SnapshotRefreshResult(day, len(new_rows), len(updated_rows))
