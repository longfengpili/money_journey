from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.utils import timezone
import csv
import io
from datetime import datetime, timedelta
from decimal import Decimal

from funds.models import FundRecord, FundSnapshot
from django.db.models import Sum
from accounts.models import UserProfile
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
    current_records = records.exclude(category='SAVINGS').order_by('-amount')
    other_records = records.filter(category='SAVINGS')
    return render(request, 'funds/record_list.html', {
        'records': records,
        'current_records': current_records,
        'other_records': other_records
    })


@login_required
def add_record(request):
    """用户添加资金记录"""
    # 超级管理员无需批准检查
    if not request.user.is_superuser:
        # 检查用户是否被批准
        try:
            profile = UserProfile.objects.get(user=request.user)
            if not profile.is_approved:
                messages.error(request, '您的账户尚未被管理员批准，无法添加记录')
                return redirect('index')
        except UserProfile.DoesNotExist:
            # 如果没有用户资料，创建并标记为未批准
            UserProfile.objects.create(user=request.user, is_approved=False)
            messages.error(request, '您的账户尚未被管理员批准，无法添加记录')
            return redirect('index')

    if request.method == 'POST':
        try:
            # 获取表单数据
            bank = request.POST.get('bank')
            category = request.POST.get('category')
            savings_status = request.POST.get('savings_status', 'ACTIVE')
            amount = request.POST.get('amount')
            interest_rate = request.POST.get('interest_rate', None)
            deposit_period = request.POST.get('deposit_period', None)
            due_date = request.POST.get('due_date', None)
            owner = request.POST.get('owner', '').strip()

            # 验证必填字段
            if not bank or not category or not amount:
                messages.error(request, '银行、类别和金额是必填字段')
                return redirect('funds:add_record')

            # 处理所有者字段
            user_obj = request.user
            final_owner = request.user.username

            if owner:
                # 检查用户权限
                if request.user.is_superuser:
                    # 超级管理员可以指定任意用户
                    try:
                        user_obj = User.objects.get(username=owner)
                        final_owner = owner
                    except User.DoesNotExist:
                        messages.error(request, f'所有者"{owner}"不存在')
                        return redirect('funds:add_record')
                else:
                    # 普通用户只能指定自己
                    if owner != request.user.username:
                        messages.error(request, f'您只能指定自己作为所有者，当前登录用户为"{request.user.username}"')
                        return redirect('funds:add_record')
                    else:
                        user_obj = request.user
                        final_owner = owner
            else:
                # 未指定所有者，使用当前用户
                user_obj = request.user
                final_owner = request.user.username

            # 创建记录
            record = FundRecord(
                user=user_obj,
                bank=bank,
                owner=final_owner,
                category=category,
                savings_status=savings_status,
                amount=amount,
                interest_rate=interest_rate if interest_rate else None,
                deposit_period=int(deposit_period) if deposit_period and deposit_period.isdigit() else None,
                due_date=datetime.strptime(due_date, '%Y-%m-%d').date() if due_date else None,
            )
            record.save()

            messages.success(request, '资金记录添加成功！')
            return  redirect('funds:record_list')
        except Exception as e:
            messages.error(request, f'添加记录失败: {str(e)}')
            return redirect('funds:add_record')

    # GET请求：显示表单
    context = {
        'bank_choices': FundRecord.BANK_CHOICES,
        'category_choices': FundRecord.CATEGORY_CHOICES,
        'savings_status_choices': FundRecord.SAVINGS_STATUS_CHOICES,
        'is_superuser': request.user.is_superuser,
    }

    # 如果是超级管理员，获取用户列表
    if request.user.is_superuser:
        users = User.objects.all().order_by('username')
        context['users'] = users
    else:
        # 普通用户只能看到自己的用户名
        context['users'] = User.objects.filter(username=request.user.username)
    return render(request, 'funds/add_record.html', context)


@login_required
def edit_record(request, record_id):
    """编辑资金记录"""
    # 获取记录
    try:
        record = FundRecord.objects.get(id=record_id)
    except FundRecord.DoesNotExist:
        messages.error(request, '资金记录不存在')
        return redirect('funds:record_list')

    # 检查用户权限
    if not request.user.is_superuser and record.user != request.user:
        messages.error(request, '您没有权限编辑此记录')
        return redirect('funds:record_list')

    # 超级管理员无需批准检查，普通用户需要检查是否已批准
    if not request.user.is_superuser:
        try:
            profile = UserProfile.objects.get(user=request.user)
            if not profile.is_approved:
                messages.error(request, '您的账户尚未被管理员批准，无法编辑记录')
                return redirect('index')
        except UserProfile.DoesNotExist:
            UserProfile.objects.create(user=request.user, is_approved=False)
            messages.error(request, '您的账户尚未被管理员批准，无法编辑记录')
            return redirect('index')

    if request.method == 'POST':
        try:
            # 获取表单数据
            bank = request.POST.get('bank')
            category = request.POST.get('category')
            savings_status = request.POST.get('savings_status', 'ACTIVE')
            amount = request.POST.get('amount')
            interest_rate = request.POST.get('interest_rate', None)
            deposit_period = request.POST.get('deposit_period', None)
            due_date = request.POST.get('due_date', None)
            owner = request.POST.get('owner', '').strip()

            # 验证必填字段
            if not bank or not category or not amount:
                messages.error(request, '银行、类别和金额是必填字段')
                return redirect('funds:edit_record', record_id=record_id)

            # 处理所有者字段
            user_obj = request.user
            final_owner = request.user.username

            if owner:
                # 检查用户权限
                if request.user.is_superuser:
                    # 超级管理员可以指定任意用户
                    try:
                        user_obj = User.objects.get(username=owner)
                        final_owner = owner
                    except User.DoesNotExist:
                        messages.error(request, f'所有者"{owner}"不存在')
                        return redirect('funds:edit_record', record_id=record_id)
                else:
                    # 普通用户只能指定自己
                    if owner != request.user.username:
                        messages.error(request, f'您只能指定自己作为所有者，当前登录用户为"{request.user.username}"')
                        return redirect('funds:edit_record', record_id=record_id)
                    else:
                        user_obj = request.user
                        final_owner = owner
            else:
                # 未指定所有者，使用当前用户
                user_obj = request.user
                final_owner = request.user.username

            # 更新记录
            record.bank = bank
            record.user = user_obj
            record.owner = final_owner
            record.category = category
            record.savings_status = savings_status
            record.amount = amount
            record.interest_rate = interest_rate if interest_rate else None
            record.deposit_period = int(deposit_period) if deposit_period and deposit_period.isdigit() else None
            record.due_date = datetime.strptime(due_date, '%Y-%m-%d').date() if due_date else None

            # 保存记录（会触发save()方法中的自动计算）
            record.save()

            messages.success(request, '资金记录更新成功！')
            return redirect('funds:record_list')
        except Exception as e:
            messages.error(request, f'更新记录失败: {str(e)}')
            return redirect('funds:edit_record', record_id=record_id)

    # GET请求：显示编辑表单
    context = {
        'record': record,
        'bank_choices': FundRecord.BANK_CHOICES,
        'category_choices': FundRecord.CATEGORY_CHOICES,
        'savings_status_choices': FundRecord.SAVINGS_STATUS_CHOICES,
        'is_superuser': request.user.is_superuser,
    }

    # 如果是超级管理员，获取用户列表
    if request.user.is_superuser:
        users = User.objects.all().order_by('username')
        context['users'] = users

    return render(request, 'funds/edit_record.html', context)


@login_required
def upload_csv(request):
    """CSV批量上传资金记录"""
    # 检查用户权限（超级管理员或已批准用户）
    if not request.user.is_superuser:
        try:
            profile = UserProfile.objects.get(user=request.user)
            if not profile.is_approved:
                messages.error(request, '您的账户尚未被管理员批准，无法上传数据')
                return redirect('index')
        except UserProfile.DoesNotExist:
            UserProfile.objects.create(user=request.user, is_approved=False)
            messages.error(request, '您的账户尚未被管理员批准，无法上传数据')
            return redirect('index')

    # 上传限制常量
    MAX_ROWS = 10000  # 最大行数限制
    BATCH_SIZE = 100  # 批量处理大小

    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']

        # 检查文件格式
        if not csv_file.name.endswith('.csv'):
            messages.error(request, '请上传CSV格式的文件')
            return redirect('funds:upload_csv')

        try:
            # 检查文件大小（限制为10MB）
            max_file_size = 10 * 1024 * 1024  # 10MB
            if csv_file.size > max_file_size:
                messages.error(request, f'文件过大（{csv_file.size // (1024*1024)}MB），请压缩文件或减少数据量，最大支持10MB')
                return redirect('funds:upload_csv')

            # 迭代读取CSV文件，避免内存溢出
            success_count = 0
            error_count = 0
            errors = []
            records_to_save = []  # 用于批量保存的临时列表

            # 使用迭代器逐行读取CSV
            try:
                # 处理可能的BOM字符
                csv_content = csv_file.read().decode('utf-8-sig')
                io_string = io.StringIO(csv_content)
                reader = csv.DictReader(io_string)
            except UnicodeDecodeError:
                messages.error(request, '文件编码错误，请使用UTF-8编码的CSV文件')
                return redirect('funds:upload_csv')

            # 检查CSV列名
            required_fields = ['bank', 'category', 'amount']
            reader_fieldnames = reader.fieldnames or []
            missing_fields = [field for field in required_fields if field not in reader_fieldnames]

            if missing_fields:
                messages.error(request, f'CSV文件缺少必要列：{", ".join(missing_fields)}')
                return redirect('funds:upload_csv')

            # 导入Django事务模块
            from django.db import transaction

            # 使用事务处理批量导入
            with transaction.atomic():
                for i, row in enumerate(reader, start=2):  # 从第2行开始（跳过标题）
                    # 行数限制检查
                    if i - 1 > MAX_ROWS:  # i从2开始，所以i-1是实际行数
                        messages.error(request, f'文件行数超过限制（最大{MAX_ROWS}行），请分批上传或减少数据量')
                        raise ValueError(f'文件行数超过限制（最大{MAX_ROWS}行）')

                    try:
                        # 验证必填字段
                        for field in required_fields:
                            if not row.get(field):
                                errors.append(f'第{i}行: {field}字段不能为空')
                                error_count += 1
                                raise ValueError(f'第{i}行: {field}字段不能为空')

                        # 处理银行字段
                        bank = row['bank'].strip().upper()
                        bank_values = [key for key, _ in FundRecord.BANK_CHOICES]

                        if bank not in bank_values:
                            # 尝试通过中文名称匹配
                            bank_mapping = {v: k for k, v in FundRecord.BANK_CHOICES}
                            if row['bank'].strip() in bank_mapping:
                                bank = bank_mapping[row['bank'].strip()]
                            else:
                                errors.append(f'第{i}行: 银行"{row["bank"]}"无效，请使用有效的银行名称')
                                error_count += 1
                                raise ValueError(f'第{i}行: 银行"{row["bank"]}"无效')

                        # 处理类别字段
                        category = row['category'].strip().upper()
                        category_values = [key for key, _ in FundRecord.CATEGORY_CHOICES]

                        if category not in category_values:
                            # 尝试通过中文名称匹配
                            category_mapping = {v: k for k, v in FundRecord.CATEGORY_CHOICES}
                            if row['category'].strip() in category_mapping:
                                category = category_mapping[row['category'].strip()]
                            else:
                                errors.append(f'第{i}行: 类别"{row["category"]}"无效，请使用有效的类别名称')
                                error_count += 1
                                raise ValueError(f'第{i}行: 类别"{row["category"]}"无效')

                        # 处理储蓄状态
                        savings_status = row.get('savings_status', 'ACTIVE').strip().upper()
                        if savings_status:
                            status_values = [key for key, _ in FundRecord.SAVINGS_STATUS_CHOICES]
                            if savings_status not in status_values:
                                # 尝试通过中文名称匹配
                                status_mapping = {v: k for k, v in FundRecord.SAVINGS_STATUS_CHOICES}
                                if row.get('savings_status', '').strip() in status_mapping:
                                    savings_status = status_mapping[row['savings_status'].strip()]
                                else:
                                    savings_status = 'ACTIVE'  # 默认值

                        # 处理金额
                        try:
                            amount = float(row['amount'])
                            if amount <= 0:
                                errors.append(f'第{i}行: 金额必须大于0')
                                error_count += 1
                                raise ValueError(f'第{i}行: 金额必须大于0')
                        except ValueError:
                            errors.append(f'第{i}行: 金额"{row["amount"]}"格式错误')
                            error_count += 1
                            raise ValueError(f'第{i}行: 金额格式错误')

                        # 处理利率
                        interest_rate = None
                        if row.get('interest_rate'):
                            try:
                                interest_rate = float(row['interest_rate'])
                            except ValueError:
                                errors.append(f'第{i}行: 利率"{row["interest_rate"]}"格式错误')
                                error_count += 1
                                raise ValueError(f'第{i}行: 利率格式错误')

                        # 处理存期
                        deposit_period = None
                        if row.get('deposit_period'):
                            try:
                                deposit_period = int(row['deposit_period'])
                            except ValueError:
                                errors.append(f'第{i}行: 存期"{row["deposit_period"]}"格式错误')
                                error_count += 1
                                raise ValueError(f'第{i}行: 存期格式错误')

                        # 处理到期日
                        due_date = None
                        if row.get('due_date'):
                            try:
                                # 尝试多种日期格式
                                for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%Y%m%d'):
                                    try:
                                        due_date = datetime.strptime(row['due_date'], fmt).date()
                                        break
                                    except ValueError:
                                        continue
                                if not due_date:
                                    errors.append(f'第{i}行: 到期日"{row["due_date"]}"格式错误，请使用YYYY-MM-DD格式')
                                    error_count += 1
                                    raise ValueError(f'第{i}行: 到期日格式错误')
                            except Exception:
                                errors.append(f'第{i}行: 到期日"{row["due_date"]}"格式错误')
                                error_count += 1
                                raise ValueError(f'第{i}行: 到期日格式错误')

                        # 处理所有者字段
                        owner_username = None
                        user_obj = request.user

                        if row.get('owner'):
                            owner_username = row['owner'].strip()
                            if owner_username:
                                # 检查用户权限
                                if request.user.is_superuser:
                                    # 超级管理员可以指定任意用户
                                    try:
                                        user_obj = User.objects.get(username=owner_username)
                                    except User.DoesNotExist:
                                        errors.append(f'第{i}行: 所有者"{owner_username}"不存在')
                                        error_count += 1
                                        raise ValueError(f'第{i}行: 所有者不存在')
                                else:
                                    # 普通用户只能指定自己
                                    if owner_username != request.user.username:
                                        errors.append(f'第{i}行: 您只能指定自己作为所有者，当前登录用户为"{request.user.username}"')
                                        error_count += 1
                                        raise ValueError(f'第{i}行: 所有者权限错误')
                                    else:
                                        user_obj = request.user

                        # 确定最终的所有者用户名
                        final_owner = owner_username if owner_username else request.user.username

                        # 计算到期月（如果提供了到期日）
                        due_month = None
                        if due_date:
                            due_month = due_date.strftime('%Y-%m')
                        
                        if due_date and deposit_period and not row.get('start_date'):
                            start_date = due_date - timedelta(days=365 * deposit_period)

                        # 创建记录对象
                        record = FundRecord(
                            user=user_obj,
                            bank=bank,
                            owner=final_owner,
                            category=category,
                            savings_status=savings_status,
                            amount=amount,
                            interest_rate=interest_rate,
                            deposit_period=deposit_period,
                            start_date=start_date,
                            due_date=due_date,
                            due_month=due_month,
                        )

                        # 添加到批量保存列表
                        records_to_save.append(record)

                        # 批量保存，每BATCH_SIZE条提交一次
                        if len(records_to_save) >= BATCH_SIZE:
                            FundRecord.objects.bulk_create(records_to_save)
                            success_count += len(records_to_save)
                            records_to_save = []

                    except ValueError as e:
                        # 这是预期的验证错误，已经添加到errors列表
                        # 继续处理下一行
                        continue
                    except Exception as e:
                        # 捕获其他异常
                        errors.append(f'第{i}行: {str(e)}')
                        error_count += 1

                # 保存剩余未提交的记录
                if records_to_save:
                    FundRecord.objects.bulk_create(records_to_save)
                    success_count += len(records_to_save)

            # 显示结果
            if success_count > 0:
                messages.success(request, f'成功导入 {success_count} 条记录')
            if error_count > 0:
                messages.warning(request, f'有 {error_count} 条记录导入失败')
            if errors:
                # 显示前5个错误
                for error in errors[:5]:
                    messages.error(request, error)
                if len(errors) > 5:
                    messages.error(request, f'... 还有 {len(errors) - 5} 个错误未显示')

            return redirect('funds:record_list')

        except Exception as e:
            messages.error(request, f'处理CSV文件时出错: {str(e)}')
            return redirect('funds:upload_csv')

    # GET请求：显示上传表单
    return render(request, 'funds/upload_csv.html')


@login_required
def download_csv_template(request):
    """下载CSV模板文件"""
    # 检查用户权限（超级管理员或已批准用户）
    if not request.user.is_superuser:
        try:
            profile = UserProfile.objects.get(user=request.user)
            if not profile.is_approved:
                messages.error(request, '您的账户尚未被管理员批准，无法下载模板')
                return redirect('index')
        except UserProfile.DoesNotExist:
            UserProfile.objects.create(user=request.user, is_approved=False)
            messages.error(request, '您的账户尚未被管理员批准，无法下载模板')
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
        '{{当前用户名}}',  # 所有者（可选，如不填写则使用当前登录用户）
        'ICBC',  # 银行（可用值: ICBC, CCB, ABC, BOC, CMB, CITIC, SPDB, CIB, CMBC, PINGAN, OTHER）
        'SAVINGS',  # 类别（可用值: CURRENT, SAVINGS, TIME_DEPOSIT, WEALTH_MANAGEMENT, FUND, STOCK, BOND, INSURANCE, OTHER）
        '10000.00',  # 金额（必须大于0）
        'ACTIVE',  # 储蓄状态（可用值: ACTIVE, MATURED, WITHDRAWN, ROLLED_OVER，默认为ACTIVE）
        '2.5',  # 利率（百分比，可选）
        '1',  # 存期（年，可选）
        '2026-12-31'  # 到期日（YYYY-MM-DD格式，可选）
    ])

    # 写入说明行
    writer.writerow([])
    writer.writerow(['说明:'])
    writer.writerow(['1. 第一行是标题行，请不要修改列名'])
    writer.writerow(['2. owner字段为可选字段，如不填写则使用当前登录用户作为所有者'])
    writer.writerow(['3. bank字段可以使用中文名称或英文代码'])
    writer.writerow(['4. category字段可以使用中文名称或英文代码'])
    writer.writerow(['5. savings_status字段可以使用中文名称或英文代码'])
    writer.writerow(['6. amount必须为大于0的数字'])
    writer.writerow(['7. interest_rate、deposit_period、due_date为可选字段'])
    writer.writerow(['8. deposit_period字段单位为年'])

    return response


@login_required
@require_POST
def create_snapshot(request):
    """创建资金快照（仅限登陆用户）"""
    if not request.user.is_authenticated:
        messages.error(request, '只有登陆才可以创建快照')
        return redirect('funds:record_list')
    
    today = timezone.now().date()
    if FundSnapshot.objects.filter(snapshot_date=today).exists():
        messages.warning(request, '今日已经创建了快照，无需重复创建')
        return redirect('funds:record_list')

    users = User.objects.all()
    try:
        for user in users:
            # 获取当前所有ACTIVE状态的记录
            active_records = FundRecord.objects.filter(savings_status='ACTIVE', user=user)

            # 计算总金额和记录数量
            total_amount_result = active_records.aggregate(total=Sum('amount'))['total']
            total_amount = total_amount_result if total_amount_result is not None else Decimal('0')
            record_count = active_records.count()

            # 按银行汇总（将Decimal转换为float以便JSON序列化）
            bank_summary = {}
            for bank, total in active_records.values('bank').annotate(
                total=Sum('amount')
            ).values_list('bank', 'total'):
                bank_summary[bank] = float(total) if total else 0.0

            # 按类别汇总（将Decimal转换为float以便JSON序列化）
            category_summary = {}
            for category, total in active_records.values('category').annotate(
                total=Sum('amount')
            ).values_list('category', 'total'):
                category_summary[category] = float(total) if total else 0.0

            # 创建快照
            snapshot = FundSnapshot.objects.create(
                created_by=request.user,
                user=user,
                total_amount=total_amount,
                record_count=record_count,
                bank_summary=bank_summary,
                category_summary=category_summary
            )

            messages.success(request, f'{user.username}的快照创建成功！总金额：¥{total_amount:,.2f}，记录数：{record_count}')

    except Exception as e:
        messages.error(request, f'创建快照失败：{str(e)}')

    return redirect('funds:record_list')
