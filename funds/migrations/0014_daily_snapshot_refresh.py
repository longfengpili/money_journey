from django.conf import settings
from django.db import migrations, models
from django.db.models import Count
import django.db.models.deletion
import django.utils.timezone


def check_duplicate_user_days(apps, schema_editor):
    snapshot_model = apps.get_model('funds', 'FundSnapshot')
    duplicate = (
        snapshot_model.objects.using(schema_editor.connection.alias)
        .filter(
            user__isnull=False,
        )
        .values('user_id', 'snapshot_date')
        .annotate(
            row_count=Count('pk'),
        )
        .filter(row_count__gt=1)
        .order_by('snapshot_date', 'user_id')
        .first()
    )
    if duplicate:
        raise RuntimeError(
            f"用户 {duplicate['user_id']} 在 {duplicate['snapshot_date']} 存在重复快照。"
            '请运行 python manage.py audit_snapshots 核对并处理重复记录后重试迁移。'
        )


class Migration(migrations.Migration):
    dependencies = [('funds', '0013_fundrecord_created_by')]

    operations = [
        migrations.RunPython(
            check_duplicate_user_days, migrations.RunPython.noop
        ),
        migrations.AlterField(
            model_name='fundsnapshot',
            name='owner',
            field=models.CharField(
                blank=True,
                null=True,
                max_length=150,
                help_text='快照所属用户',
                verbose_name='所有者',
            ),
        ),
        migrations.AlterField(
            model_name='fundsnapshot',
            name='created_by',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='created_fund_snapshots',
                to=settings.AUTH_USER_MODEL,
                verbose_name='最近生成者',
            ),
        ),
        migrations.AlterField(
            model_name='fundsnapshot',
            name='snapshot_date',
            field=models.DateField(
                default=django.utils.timezone.localdate,
                verbose_name='快照时间',
            ),
        ),
        migrations.AddConstraint(
            model_name='fundsnapshot',
            constraint=models.UniqueConstraint(
                fields=('user', 'snapshot_date'),
                name='unique_snapshot_user_date',
            ),
        ),
    ]
