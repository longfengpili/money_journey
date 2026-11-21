from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction

from funds.models import FundRecord


class Command(BaseCommand):
    help = '核对资产账号归属，默认只读，--apply 仅补齐用户名精确匹配的空关联'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true')

    def handle(self, *args, **options):
        repaired = 0
        records = (
            FundRecord.objects.select_related('user')
            .only(
                'pk',
                'user',
                'owner',
                'user__username',
            )
            .order_by('pk')
        )
        for record in records:
            if record.user_id:
                state = (
                    '一致'
                    if record.owner == record.user.username
                    else '文本冲突'
                )
            else:
                state = '待核对'
                with transaction.atomic():
                    matches = list(User.objects.filter(username=record.owner))
                    # 数据库排序规则可能忽略大小写，必须再次精确比较。
                    if (
                        len(matches) == 1
                        and matches[0].username == record.owner
                    ):
                        state = '可补齐'
                        if options['apply']:
                            repaired += FundRecord.objects.filter(
                                pk=record.pk,
                                user__isnull=True,
                                owner=record.owner,
                            ).update(user=matches[0])
            self.stdout.write(
                f'{record.pk}\t{state}\t账号={record.user_id}\t文本={record.owner}'
            )
        self.stdout.write(
            f'已补齐 {repaired} 条' if options['apply'] else '只读核对完成'
        )
