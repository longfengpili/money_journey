from django.contrib import admin
from funds.models import FundRecord, FundSnapshot


@admin.register(FundRecord)
class FundRecordAdmin(admin.ModelAdmin):
    list_display = ('owner', 'bank', 'category', 'amount', 'interest_rate', 'due_date', 'savings_status', 'created_at')
    list_filter = ('bank', 'owner', 'category', 'savings_status', 'due_month')
    search_fields = ('owner', 'bank', 'category')
    list_editable = ('savings_status',)
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('基本信息', {
            'fields': ('bank', 'owner', 'category', 'savings_status')
        }),
        ('金额信息', {
            'fields': ('amount', 'interest_rate')
        }),
        ('期限信息', {
            'fields': ('deposit_period', 'due_date', 'due_month')
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    date_hierarchy = 'due_date'


@admin.register(FundSnapshot)
class FundSnapshotAdmin(admin.ModelAdmin):
    list_display = ('snapshot_date', 'created_by', 'total_amount', 'record_count', 'created_at')
    list_filter = ('created_by', 'snapshot_date')
    search_fields = ('created_by__username',)
    readonly_fields = ('created_at', 'updated_at', 'bank_summary', 'category_summary')
    fieldsets = (
        ('基本信息', {
            'fields': ('created_by', 'snapshot_date', 'total_amount', 'record_count')
        }),
        ('汇总数据', {
            'fields': ('bank_summary', 'category_summary')
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    date_hierarchy = 'snapshot_date'