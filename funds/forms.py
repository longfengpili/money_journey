"""页面和 CSV 共用的资金字段校验。"""

from django import forms
from django.core.exceptions import PermissionDenied, ValidationError

from accounts.permissions import can_edit_record
from funds.models import FundRecord
from funds.permissions import resolve_record_owner

DATE_FORMATS = ('%Y-%m-%d', '%Y/%m/%d', '%Y%m%d')


class FundRecordForm(forms.ModelForm):
    owner = forms.CharField(label='所有者', required=False, max_length=150)
    interest_rate = forms.DecimalField(
        label='利率(%)',
        required=False,
        min_value=0,
        max_digits=5,
        decimal_places=2,
    )
    deposit_period = forms.IntegerField(
        label='存期(年)',
        required=False,
        min_value=1,
    )
    due_date = forms.DateField(
        label='到期日',
        required=False,
        input_formats=DATE_FORMATS,
        widget=forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
    )
    start_date = forms.DateField(
        label='开始日期',
        required=False,
        input_formats=DATE_FORMATS,
    )

    class Meta:
        model = FundRecord
        fields = (
            'owner',
            'bank',
            'category',
            'savings_status',
            'amount',
            'interest_rate',
            'deposit_period',
            'due_date',
        )

    def __init__(
        self, data=None, *, actor, instance=None, owner_resolver=None
    ):
        self.actor = actor
        self.owner_resolver = owner_resolver or resolve_record_owner
        self.owner_user = None
        super().__init__(data=data, instance=instance)
        self.initial['owner'] = (
            self.instance.user.username
            if self.instance.user_id
            else ('' if self.instance.pk else actor.username)
        )
        self.fields['savings_status'].required = False
        # 模型默认值不会覆盖显式提交的空字符串。
        self.fields['savings_status'].initial = 'ACTIVE'
        for field in self.fields.values():
            css = (
                'form-select'
                if isinstance(field.widget, forms.Select)
                else 'form-control'
            )
            field.widget.attrs['class'] = css

    def clean_owner(self):
        username = self.cleaned_data['owner']
        if self.instance.pk and not can_edit_record(self.actor, self.instance):
            raise ValidationError('您没有权限编辑此记录')
        if self.instance.pk and self.instance.user_id is None and not username:
            raise ValidationError('请先明确该历史资产的所有者')
        try:
            self.owner_user = self.owner_resolver(
                self.actor,
                username,
                current_owner=self.instance.user,
            )
        except (PermissionDenied, ValueError) as exc:
            raise ValidationError(str(exc)) from exc
        return self.owner_user.username

    def clean_savings_status(self):
        return self.cleaned_data['savings_status'] or 'ACTIVE'

    def _post_clean(self):
        super()._post_clean()
        if self.errors:
            return
        self.instance.user = self.owner_user
        if not self.instance.pk:
            self.instance.created_by = self.actor
        if 'start_date' in self.data:
            self.instance.start_date = self.cleaned_data['start_date']
        # 批量保存同样使用这里的衍生字段，日期越界回到表单错误。
        try:
            self.instance.prepare_derived_fields()
        except ValidationError as exc:
            self._update_errors(exc)
