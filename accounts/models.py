from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


class UserProfile(models.Model):
    """用户扩展资料"""
    id = models.AutoField(primary_key=True)  # 显式定义主键字段
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name='用户')
    is_approved = models.BooleanField('已批准', default=False, help_text='用户注册后需要管理员批准才能登录')
    created_at = models.DateTimeField('创建时间', default=timezone.now)

    class Meta:
        verbose_name = '用户资料'
        verbose_name_plural = '用户资料'
        db_table = 'records_userprofile'  # 使用原表名以保持数据兼容

    def __str__(self):
        return f"{self.user.username} - {'已批准' if self.is_approved else '待批准'}"