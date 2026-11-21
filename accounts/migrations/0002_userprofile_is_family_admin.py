from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('accounts', '0001_initial')]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='is_family_admin',
            field=models.BooleanField(
                default=False, verbose_name='家庭管理员'
            ),
        ),
    ]
