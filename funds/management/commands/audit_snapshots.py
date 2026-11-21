from django.core.management.base import BaseCommand
from django.db.models import Count

from funds.models import FundRecord, FundSnapshot


class Command(BaseCommand):
    help = '只读核对重复用户日快照、未关联快照及存续资产归属'

    def handle(self, *args, **options):
        duplicates = (
            FundSnapshot.objects.filter(user__isnull=False)
            .values(
                'user_id',
                'snapshot_date',
            )
            .annotate(row_count=Count('pk'))
            .filter(row_count__gt=1)
            .order_by(
                'snapshot_date',
                'user_id',
            )
        )
        for group in duplicates:
            ids = list(
                FundSnapshot.objects.filter(
                    user_id=group['user_id'],
                    snapshot_date=group['snapshot_date'],
                )
                .order_by('pk')
                .values_list('pk', flat=True)
            )
            self.stdout.write(
                f"重复用户日：用户={group['user_id']} "
                f"日期={group['snapshot_date']} 快照ID={ids}"
            )
        snapshots = list(
            FundSnapshot.objects.filter(user__isnull=True)
            .order_by('pk')
            .values_list('pk', flat=True)
        )
        assets = list(
            FundRecord.objects.filter(
                user__isnull=True, savings_status='ACTIVE'
            )
            .order_by('pk')
            .values_list('pk', flat=True)
        )
        self.stdout.write(f'未关联账号的快照ID：{snapshots}')
        self.stdout.write(f'未关联账号的存续资产ID：{assets}')
        self.stdout.write('只读核对完成')
