from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.contrib.auth.models import User

class UserProfile(models.Model):
    """用户扩展资料"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name='用户')
    is_approved = models.BooleanField('已批准', default=False, help_text='用户注册后需要管理员批准才能登录')
    created_at = models.DateTimeField('创建时间', default=timezone.now)

    class Meta:
        verbose_name = '用户资料'
        verbose_name_plural = '用户资料'

    def __str__(self):
        return f"{self.user.username} - {'已批准' if self.is_approved else '待批准'}"


class FundRecord(models.Model):
    # 银行选择
    BANK_CHOICES = [
        ('ICBC', '工商银行'),
        ('CCB', '建设银行'),
        ('ABC', '农业银行'),
        ('RCB', '农商银行'),
        ('BOC', '中国银行'),
        ('CMB', '招商银行'),
        ('CITIC', '中信银行'),
        ('SPDB', '浦发银行'),
        ('CIB', '兴业银行'),
        ('CMBC', '民生银行'),
        ('PINGAN', '平安银行'),
        ('ALIPAY', '支付宝'), 
        ('WECHAT', '微信支付'), 
        ('HPP', '公积金'), 
        ('STOCK', '股票'),
        ('OTHER', '其他银行'),
    ]

    # 类别选择
    CATEGORY_CHOICES = [
        ('CURRENT', '活期存款'),
        ('SAVINGS', '储蓄存款'),
        ('TIME_DEPOSIT', '定期存款'),
        ('WEALTH_MANAGEMENT', '理财产品'),
        ('FUND', '基金'),
        ('STOCK', '股票'),
        ('BOND', '债券'),
        ('INSURANCE', '保险'),
        ('OTHER', '其他'),
    ]

    # 储蓄状态选择
    SAVINGS_STATUS_CHOICES = [
        ('ACTIVE', '存续中'),
        ('MATURED', '已到期'),
        ('WITHDRAWN', '已取出'),
        ('ROLLED_OVER', '已续存'),
    ]

    bank = models.CharField('银行', max_length=50, choices=BANK_CHOICES)
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='关联用户', null=True, blank=True, help_text='记录所属用户')
    owner = models.CharField('所有者', max_length=100, blank=True, help_text='自动从用户信息填充')
    category = models.CharField('类别', max_length=50, choices=CATEGORY_CHOICES)
    savings_status = models.CharField('储蓄状态', max_length=50, choices=SAVINGS_STATUS_CHOICES, default='ACTIVE')
    amount = models.DecimalField('金额', max_digits=15, decimal_places=2, validators=[MinValueValidator(0)])
    interest_rate = models.DecimalField('利率(%)', max_digits=5, decimal_places=2, null=True, blank=True)
    deposit_period = models.IntegerField('存期(月)', null=True, blank=True, help_text='单位为月')
    due_date = models.DateField('到期日', null=True, blank=True)
    due_month = models.CharField('到期月', max_length=7, null=True, blank=True, help_text='格式: YYYY-MM')
    created_at = models.DateTimeField('创建时间', default=timezone.now)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '资金记录'
        verbose_name_plural = '资金记录'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.owner} - {self.get_bank_display()} - {self.amount}"

    def save(self, *args, **kwargs):
        # 自动填充所有者信息
        if self.user and not self.owner:
            self.owner = self.user.username

        # 如果提供了到期日，自动计算到期月（强制计算，不允许手动修改）
        if self.due_date:
            self.due_month = self.due_date.strftime('%Y-%m')

        super().save(*args, **kwargs)