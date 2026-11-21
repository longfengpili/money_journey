from django.contrib import admin
from django.core.exceptions import PermissionDenied, ValidationError

from accounts.permissions import (
    can_edit_record,
    can_write_assets,
    is_family_admin,
)
from funds.models import FundRecord, FundSnapshot
from funds.permissions import resolve_record_owner


@admin.register(FundRecord)
class FundRecordAdmin(admin.ModelAdmin):
    list_display = (
        'owner_display',
        'bank',
        'category',
        'amount',
        'interest_rate',
        'due_date',
        'savings_status',
        'created_at',
    )
    list_filter = ('bank', 'user', 'category', 'savings_status', 'due_month')
    search_fields = (
        'user__username',
        'user__first_name',
        'owner',
        'bank',
        'category',
    )
    list_editable = ('savings_status',)
    readonly_fields = ('owner', 'created_by', 'created_at', 'updated_at')
    fieldsets = (
        (
            '基本信息',
            {
                'fields': (
                    'bank',
                    'user',
                    'owner',
                    'created_by',
                    'category',
                    'savings_status',
                )
            },
        ),
        ('金额信息', {'fields': ('amount', 'interest_rate')}),
        ('期限信息', {'fields': ('deposit_period', 'due_date', 'due_month')}),
        ('时间信息', {'fields': ('created_at', 'updated_at')}),
    )
    date_hierarchy = 'due_date'

    def has_add_permission(self, request):
        return can_write_assets(request.user) and super().has_add_permission(
            request
        )

    def has_change_permission(self, request, obj=None):
        allowed = (
            can_write_assets(request.user)
            if obj is None
            else can_edit_record(request.user, obj)
        )
        return allowed and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        allowed = (
            can_write_assets(request.user)
            if obj is None
            else can_edit_record(request.user, obj)
        )
        return allowed and super().has_delete_permission(request, obj)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'user':
            from django.contrib.auth.models import User

            kwargs['queryset'] = User.objects.all()
            if not is_family_admin(request.user):
                kwargs['queryset'] = kwargs['queryset'].filter(
                    pk=request.user.pk
                )
            kwargs['required'] = True
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def _permission_form(self, form_class, request):
        class PermissionForm(form_class):
            def clean(self):
                cleaned = super().clean()
                if not self.has_changed():
                    return cleaned
                if self.instance.pk and not can_edit_record(
                    request.user, self.instance
                ):
                    raise ValidationError('您没有权限编辑此记录')
                owner = cleaned.get('user')
                if owner:
                    try:
                        resolve_record_owner(request.user, owner.username)
                    except PermissionDenied as exc:
                        raise ValidationError(str(exc)) from exc
                return cleaned

        return PermissionForm

    def get_form(self, request, obj=None, **kwargs):
        return self._permission_form(
            super().get_form(request, obj, **kwargs), request
        )

    def get_changelist_form(self, request, **kwargs):
        return self._permission_form(
            super().get_changelist_form(request, **kwargs), request
        )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def delete_queryset(self, request, queryset):
        if any(
            not can_edit_record(request.user, record) for record in queryset
        ):
            raise PermissionDenied('只能删除自己名下的资产')
        super().delete_queryset(request, queryset)


@admin.register(FundSnapshot)
class FundSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        'snapshot_date',
        'owner',
        'created_by',
        'total_amount',
        'record_count',
        'created_at',
    )
    list_filter = ('created_by', 'snapshot_date')
    search_fields = ('owner', 'user__username', 'created_by__username')
    readonly_fields = (
        'user',
        'owner',
        'created_by',
        'snapshot_date',
        'total_amount',
        'record_count',
        'created_at',
        'updated_at',
        'bank_summary',
        'category_summary',
    )
    fieldsets = (
        (
            '基本信息',
            {
                'fields': (
                    'user',
                    'owner',
                    'created_by',
                    'snapshot_date',
                    'total_amount',
                    'record_count',
                )
            },
        ),
        ('汇总数据', {'fields': ('bank_summary', 'category_summary')}),
        ('时间信息', {'fields': ('created_at', 'updated_at')}),
    )
    date_hierarchy = 'snapshot_date'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return can_write_assets(request.user) and super().has_view_permission(
            request, obj
        )

    def has_delete_permission(self, request, obj=None):
        return is_family_admin(request.user) and super().has_delete_permission(
            request, obj
        )
