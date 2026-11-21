from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('accounts', '0002_userprofile_is_family_admin')]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='is_archived',
            field=models.BooleanField(default=False, verbose_name='已从家庭移除'),
        ),
    ]
