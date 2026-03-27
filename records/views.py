from django.shortcuts import render, redirect
from django.db.models import Sum, Count
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from .models import FundRecord, UserProfile
import csv
import io
from datetime import datetime

def index(request):
    """首页视图"""
    return render(request, 'records/index.html')

@login_required
def dashboard(request):
    """仪表板视图 - 显示汇总数据"""
    # 创建选择项映射字典
    bank_choices = dict(FundRecord.BANK_CHOICES)
    category_choices = dict(FundRecord.CATEGORY_CHOICES)
    savings_status_choices = dict(FundRecord.SAVINGS_STATUS_CHOICES)

    # 根据用户权限确定查询集
    if request.user.is_superuser:
        active_records = FundRecord.objects.filter(savings_status='ACTIVE').order_by('-due_date')
        all_records = FundRecord.objects.all()
    else:
        active_records = FundRecord.objects.filter(user=request.user, savings_status='ACTIVE').order_by('-due_date')
        all_records = FundRecord.objects.filter(user=request.user)

    # 按所有者汇总（使用ACTIVE记录）
    owner_summary = active_records.values('owner').annotate(
        total_amount=Sum('amount'),
        record_count=Count('id')
    ).order_by('-total_amount')

    # 按银行汇总（使用ACTIVE记录）
    bank_summary_raw = active_records.values('bank').annotate(
        total_amount=Sum('amount'),
        record_count=Count('id')
    ).order_by('-total_amount')

    # 转换银行汇总数据，添加显示标签
    bank_summary = []
    for item in bank_summary_raw:
        item_dict = dict(item)
        item_dict['bank_display'] = bank_choices.get(item['bank'], item['bank'])
        bank_summary.append(item_dict)

    # 按类别汇总（使用ACTIVE记录）
    category_summary_raw = active_records.values('category').annotate(
        total_amount=Sum('amount'),
        record_count=Count('id')
    ).order_by('-total_amount')

    # 转换类别汇总数据，添加显示标签
    category_summary = []
    for item in category_summary_raw:
        item_dict = dict(item)
        item_dict['category_display'] = category_choices.get(item['category'], item['category'])
        category_summary.append(item_dict)

    # 按储蓄状态汇总（使用所有记录）
    status_summary_raw = active_records.values('savings_status').annotate(
        total_amount=Sum('amount'),
        record_count=Count('id')
    ).order_by('-total_amount')

    # 转换储蓄状态汇总数据，添加显示标签
    status_summary = []
    for item in status_summary_raw:
        item_dict = dict(item)
        item_dict['savings_status_display'] = savings_status_choices.get(item['savings_status'], item['savings_status'])
        status_summary.append(item_dict)

    # 总金额（使用ACTIVE记录）
    total_amount = active_records.aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'owner_summary': owner_summary,
        'bank_summary': bank_summary,
        'category_summary': category_summary,
        'status_summary': status_summary,
        'total_amount': total_amount,
    }
    return render(request, 'records/dashboard.html', context)

@login_required
def record_list(request):
    """资金记录列表"""
    if request.user.is_superuser:
        records = FundRecord.objects.filter(savings_status='ACTIVE').order_by('due_date')
    else:
        records = FundRecord.objects.filter(user=request.user, savings_status='ACTIVE').order_by('due_date')
    return render(request, 'records/record_list.html', {'records': records})

@login_required
def charts(request):
    """图表展示页面"""
    # 根据用户权限确定查询集
    if request.user.is_superuser:
        records = FundRecord.objects.filter(savings_status='ACTIVE').order_by('due_date')
    else:
        records = FundRecord.objects.filter(user=request.user, savings_status='ACTIVE').order_by('due_date')

    # 获取图表数据
    owner_data = records.values('owner').annotate(total=Sum('amount')).order_by('-total')
    bank_data = records.values('bank').annotate(total=Sum('amount')).order_by('-total')
    category_data = records.values('category').annotate(total=Sum('amount')).order_by('-total')

    # 创建银行选择项映射字典
    bank_choices = dict(FundRecord.BANK_CHOICES)
    category_choices = dict(FundRecord.CATEGORY_CHOICES)

    # 转换数据格式便于Chart.js使用
    owner_labels = [item['owner'] for item in owner_data]
    owner_totals = [float(item['total']) for item in owner_data]

    bank_labels = [bank_choices.get(item['bank'], item['bank']) for item in bank_data]
    bank_totals = [float(item['total']) for item in bank_data]

    category_labels = [category_choices.get(item['category'], item['category']) for item in category_data]
    category_totals = [float(item['total']) for item in category_data]

    context = {
        'owner_labels': owner_labels,
        'owner_totals': owner_totals,
        'bank_labels': bank_labels,
        'bank_totals': bank_totals,
        'category_labels': category_labels,
        'category_totals': category_totals,
    }
    return render(request, 'records/charts.html', context)


from django.contrib.auth.views import LoginView
from django.http import HttpResponseRedirect


class CustomLoginView(LoginView):
    """自定义登录视图，检查用户是否被批准"""

    def form_valid(self, form):
        # 先执行父类的登录逻辑
        response = super().form_valid(form)
        user = self.request.user

        # 超级管理员无需批准检查
        if user.is_superuser:
            return response

        # 检查用户是否被批准
        try:
            profile = UserProfile.objects.get(user=user)
            if not profile.is_approved:
                # 用户未批准，注销并显示消息
                logout(self.request)
                messages.error(self.request, '您的账户尚未被管理员批准，请等待批准后再登录。')
                return redirect('login')
        except UserProfile.DoesNotExist:
            # 如果没有用户资料，创建并标记为未批准
            UserProfile.objects.create(user=user, is_approved=False)
            messages.error(self.request, '您的账户尚未被管理员批准，请等待批准后再登录。')
            logout(self.request)
            return redirect('login')

        return response


def register(request):
    """用户注册视图"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        email = request.POST.get('email', '')

        # 验证输入
        if not username or not password:
            messages.error(request, '用户名和密码不能为空')
            return redirect('register')

        if password != password2:
            messages.error(request, '两次输入的密码不一致')
            return redirect('register')

        # 检查用户名是否已存在
        if User.objects.filter(username=username).exists():
            messages.error(request, '用户名已存在')
            return redirect('register')

        # 创建用户
        try:
            user = User.objects.create_user(username=username, password=password, email=email)
            user.is_active = True  # 用户可登录，但需要批准
            user.save()

            # 创建用户资料
            UserProfile.objects.create(user=user, is_approved=False)

            messages.success(request, '注册成功！请等待管理员批准您的账户。')
            return redirect('login')
        except Exception as e:
            messages.error(request, f'注册失败: {str(e)}')
            return redirect('register')

    return render(request, 'registration/register.html')


@login_required
def user_approval_list(request):
    """管理员查看待批准用户列表"""
    if not request.user.is_superuser:
        messages.error(request, '只有管理员可以访问此页面')
        return redirect('index')

    pending_users = UserProfile.objects.filter(is_approved=False).select_related('user')
    return render(request, 'registration/user_approval_list.html', {'pending_users': pending_users})


@login_required
@require_POST
@csrf_protect
def approve_user(request, user_id):
    """管理员批准用户（POST请求）"""
    if not request.user.is_superuser:
        messages.error(request, '只有管理员可以执行此操作')
        return redirect('index')

    try:
        user_profile = UserProfile.objects.get(user_id=user_id)
        user_profile.is_approved = True
        user_profile.save()
        messages.success(request, f'用户 {user_profile.user.username} 已批准')
    except UserProfile.DoesNotExist:
        messages.error(request, '用户不存在')

    return redirect('user_approval_list')


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
                return redirect('add_record')

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
                        return redirect('add_record')
                else:
                    # 普通用户只能指定自己
                    if owner != request.user.username:
                        messages.error(request, f'您只能指定自己作为所有者，当前登录用户为"{request.user.username}"')
                        return redirect('add_record')
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
                due_date=due_date if due_date else None,
            )
            record.save()

            messages.success(request, '资金记录添加成功！')
            return redirect('record_list')
        except Exception as e:
            messages.error(request, f'添加记录失败: {str(e)}')
            return redirect('add_record')

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

    return render(request, 'records/add_record.html', context)


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

    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']

        # 检查文件格式
        if not csv_file.name.endswith('.csv'):
            messages.error(request, '请上传CSV格式的文件')
            return redirect('upload_csv')

        try:
            # 读取CSV文件
            data_set = csv_file.read().decode('utf-8-sig')  # 处理BOM
            io_string = io.StringIO(data_set)

            # 读取CSV数据
            reader = csv.DictReader(io_string)

            # 检查CSV列名
            required_fields = ['bank', 'category', 'amount']

            success_count = 0
            error_count = 0
            errors = []

            for i, row in enumerate(reader, start=2):  # 从第2行开始（跳过标题）
                try:
                    # 验证必填字段
                    for field in required_fields:
                        if not row.get(field):
                            errors.append(f'第{i}行: {field}字段不能为空')
                            error_count += 1
                            continue

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
                            continue

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
                            continue

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
                            continue
                    except ValueError:
                        errors.append(f'第{i}行: 金额"{row["amount"]}"格式错误')
                        error_count += 1
                        continue

                    # 处理利率
                    interest_rate = None
                    if row.get('interest_rate'):
                        try:
                            interest_rate = float(row['interest_rate'])
                        except ValueError:
                            errors.append(f'第{i}行: 利率"{row["interest_rate"]}"格式错误')
                            error_count += 1
                            continue

                    # 处理存期
                    deposit_period = None
                    if row.get('deposit_period'):
                        try:
                            deposit_period = int(row['deposit_period'])
                        except ValueError:
                            errors.append(f'第{i}行: 存期"{row["deposit_period"]}"格式错误')
                            error_count += 1
                            continue

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
                                continue
                        except Exception:
                            errors.append(f'第{i}行: 到期日"{row["due_date"]}"格式错误')
                            error_count += 1
                            continue

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
                                    continue
                            else:
                                # 普通用户只能指定自己
                                if owner_username != request.user.username:
                                    errors.append(f'第{i}行: 您只能指定自己作为所有者，当前登录用户为"{request.user.username}"')
                                    error_count += 1
                                    continue
                                else:
                                    user_obj = request.user

                    # 确定最终的所有者用户名
                    final_owner = owner_username if owner_username else request.user.username

                    # 创建记录
                    record = FundRecord(
                        user=user_obj,
                        bank=bank,
                        owner=final_owner,
                        category=category,
                        savings_status=savings_status,
                        amount=amount,
                        interest_rate=interest_rate,
                        deposit_period=deposit_period,
                        due_date=due_date,
                    )
                    record.save()
                    success_count += 1

                except Exception as e:
                    errors.append(f'第{i}行: {str(e)}')
                    error_count += 1

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

            return redirect('record_list')

        except Exception as e:
            messages.error(request, f'处理CSV文件时出错: {str(e)}')
            return redirect('upload_csv')

    # GET请求：显示上传表单
    return render(request, 'records/upload_csv.html')


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
def edit_record(request, record_id):
    """编辑资金记录"""
    # 获取记录
    try:
        record = FundRecord.objects.get(id=record_id)
    except FundRecord.DoesNotExist:
        messages.error(request, '资金记录不存在')
        return redirect('record_list')

    # 检查用户权限
    if not request.user.is_superuser and record.user != request.user:
        messages.error(request, '您没有权限编辑此记录')
        return redirect('record_list')

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
                return redirect('edit_record', record_id=record_id)

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
                        return redirect('edit_record', record_id=record_id)
                else:
                    # 普通用户只能指定自己
                    if owner != request.user.username:
                        messages.error(request, f'您只能指定自己作为所有者，当前登录用户为"{request.user.username}"')
                        return redirect('edit_record', record_id=record_id)
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
            record.due_date = due_date if due_date else None

            # 保存记录（会触发save()方法中的自动计算）
            record.save()

            messages.success(request, '资金记录更新成功！')
            return redirect('record_list')
        except Exception as e:
            messages.error(request, f'更新记录失败: {str(e)}')
            return redirect('edit_record', record_id=record_id)

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

    return render(request, 'records/edit_record.html', context)