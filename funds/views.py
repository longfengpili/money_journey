import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import DatabaseError, transaction
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from accounts.permissions import (
    can_edit_record, can_write_assets, is_family_admin,
)
from funds.forms import FundRecordForm
from funds.importers import import_fund_csv
from funds.models import FundRecord
from funds.snapshots import refresh_daily_snapshots

from .demorecord import DEMO_CURRENT_RECORDS, DEMO_OTHER_RECORDS


def record_list(request):
    """资金记录列表"""
    if not request.user.is_authenticated:
        # 游客模式：返回演示数据
        return render(request, 'funds/record_list.html', {
            'records': list(DEMO_CURRENT_RECORDS) + list(DEMO_OTHER_RECORDS),
            'current_records': DEMO_CURRENT_RECORDS,
            'other_records': DEMO_OTHER_RECORDS,
        })

    # 登录用户：查询真实数据
    records = FundRecord.objects.filter(savings_status='ACTIVE').select_related('user').order_by('due_date')
    may_write = can_write_assets(request.user)
    family_admin = is_family_admin(request.user)
    for record in records:
        record.can_edit = may_write and (
            family_admin or record.user_id == request.user.pk
        )
    current_records = sorted(
        (r for r in records if r.category != 'SAVINGS'),
        key=lambda r: r.amount, reverse=True,
    )
    other_records = [r for r in records if r.category == 'SAVINGS']
    return render(request, 'funds/record_list.html', {
        'records': records,
        'current_records': current_records,
        'other_records': other_records
    })


def _record_form_context(request, form):
    family_admin = is_family_admin(request.user)
    users = User.objects.all().order_by('username')
    if not family_admin:
        users = users.filter(pk=request.user.pk)
    return {
        'form': form,
        'record': form.instance,
        'users': users,
        'is_family_admin': family_admin,
        'bank_choices': FundRecord.BANK_CHOICES,
        'category_choices': FundRecord.CATEGORY_CHOICES,
        'savings_status_choices': FundRecord.SAVINGS_STATUS_CHOICES,
    }


@login_required
def add_record(request):
    """校验通过后创建本人或管理员指定的资产。"""
    if not can_write_assets(request.user):
        messages.error(request, '您的账户尚未批准或已停用')
        return redirect('index')
    form = FundRecordForm(
        request.POST if request.method == 'POST' else None,
        actor=request.user,
    )
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                form.save()
        except DatabaseError:
            form.add_error(None, '保存失败，请稍后重试')
        else:
            messages.success(request, '资金记录添加成功！')
            return redirect('funds:record_list')
    return render(
        request, 'funds/add_record.html', _record_form_context(request, form)
    )


@login_required
@transaction.atomic
def edit_record(request, record_id):
    """锁定原记录后校验修改权限和字段。"""
    try:
        record = FundRecord.objects.select_for_update().get(pk=record_id)
    except FundRecord.DoesNotExist:
        messages.error(request, '资金记录不存在')
        return redirect('funds:record_list')
    if not can_edit_record(request.user, record):
        messages.error(request, '您没有权限编辑此记录')
        return redirect('funds:record_list')
    form = FundRecordForm(
        request.POST if request.method == 'POST' else None,
        actor=request.user,
        instance=record,
    )
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                form.save()
        except DatabaseError:
            form.add_error(None, '保存失败，请稍后重试')
        else:
            messages.success(request, '资金记录更新成功！')
            return redirect('funds:record_list')
    return render(
        request, 'funds/edit_record.html', _record_form_context(request, form)
    )


@login_required
def upload_csv(request):
    """统一校验并导入 CSV，文件或数据库失败时不报告部分成功。"""
    if not can_write_assets(request.user):
        messages.error(request, '您的账户尚未批准或已停用')
        return redirect('index')
    if request.method == 'POST' and request.FILES.get('csv_file'):
        try:
            result = import_fund_csv(
                request.FILES['csv_file'], actor=request.user
            )
        except ValidationError as exc:
            messages.error(request, '；'.join(exc.messages))
            return redirect('funds:upload_csv')
        except DatabaseError:
            messages.error(request, '导入失败，本次记录已回滚，请稍后重试')
            return redirect('funds:upload_csv')
        if result.success_count:
            messages.success(
                request, f'成功导入 {result.success_count} 条记录'
            )
        if result.error_count:
            messages.warning(
                request, f'有 {result.error_count} 条记录导入失败'
            )
        for error in result.errors:
            messages.error(request, error)
        if result.error_count > len(result.errors):
            messages.error(
                request,
                f'另有 {result.error_count - len(result.errors)} 行错误未显示',
            )
        return redirect('funds:record_list')
    return render(request, 'funds/upload_csv.html')


@login_required
def download_csv_template(request):
    """下载CSV模板文件"""
    if not can_write_assets(request.user):
        messages.error(request, '您的账户尚未批准或已停用')
        return redirect('index')

    # 创建CSV模板
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="fund_record_template.csv"'

    writer = csv.writer(response)

    # 写入标题行
    headers = [
        'owner', 'bank', 'category', 'amount', 'savings_status',
        'interest_rate', 'deposit_period', 'due_date'
    ]
    writer.writerow(headers)

    # 写入示例数据
    writer.writerow([
        '',  # 所有者（可选，如不填写则使用当前登录用户）
        'ICBC',  # 银行（可用值: ICBC, CCB, ABC, BOC, CMB, CITIC, SPDB, CIB, CMBC, PINGAN, OTHER）
        'SAVINGS',  # 类别（可用值: CURRENT, SAVINGS, TIME_DEPOSIT, WEALTH_MANAGEMENT, FUND, STOCK, BOND, INSURANCE, OTHER）
        '10000.00',  # 金额（允许为零）
        'ACTIVE',  # 储蓄状态（可用值: ACTIVE, MATURED, WITHDRAWN, ROLLED_OVER，默认为ACTIVE）
        '2.5',  # 利率（百分比，可选）
        '1',  # 存期（年，可选）
        '2026-12-31'  # 到期日（YYYY-MM-DD格式，可选）
    ])

    return response


@login_required
@require_POST
def create_snapshot(request):
    """家庭管理员原子刷新当天全部成员快照。"""
    try:
        result = refresh_daily_snapshots(request.user)
    except ValidationError as exc:
        messages.error(request, '；'.join(exc.messages))
    except DatabaseError:
        messages.error(request, '快照刷新失败，本次更改已回滚，请稍后重试')
    else:
        count = result.created_count + result.updated_count
        messages.success(
            request,
            f'已刷新 {result.snapshot_date} 的 {count} 位成员快照'
            f'（新增 {result.created_count} 条，更新 {result.updated_count} 条）',
        )
    return redirect('funds:record_list')
