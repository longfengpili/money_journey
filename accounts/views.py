from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import logout
from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.http import HttpResponseRedirect
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect

from accounts.models import UserProfile


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
                return redirect('accounts:login')
        except UserProfile.DoesNotExist:
            # 如果没有用户资料，创建并标记为未批准
            UserProfile.objects.create(user=user, is_approved=False)
            messages.error(self.request, '您的账户尚未被管理员批准，请等待批准后再登录。')
            logout(self.request)
            return redirect('accounts:login')

        return response


def register(request):
    """用户注册视图"""
    if request.method == 'POST':
        username = request.POST.get('username')
        first_name = request.POST.get('first_name', '')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        email = request.POST.get('email', '')

        # 验证输入
        if not username or not password:
            messages.error(request, '用户名和密码不能为空')
            return redirect('accounts:register')

        if password != password2:
            messages.error(request, '两次输入的密码不一致')
            return redirect('accounts:register')

        # 检查用户名是否已存在
        if User.objects.filter(username=username).exists():
            messages.error(request, '用户名已存在')
            return redirect('accounts:register')

        # 创建用户
        try:
            user = User.objects.create_user(username=username, password=password, first_name=first_name, email=email)
            user.is_active = True  # 用户可登录，但需要批准
            user.save()

            # 创建用户资料
            UserProfile.objects.create(user=user, is_approved=False)

            messages.success(request, '注册成功！请等待管理员批准您的账户。')
            return redirect('accounts:login')
        except Exception as e:
            messages.error(request, f'注册失败: {str(e)}')
            return redirect('accounts:register')

    return render(request, 'accounts/register.html')


@login_required
def user_approval_list(request):
    """管理员查看待批准用户列表"""
    if not request.user.is_superuser:
        messages.error(request, '只有管理员可以访问此页面')
        return redirect('accounts:index')

    pending_users = UserProfile.objects.filter(is_approved=False).select_related('user')
    return render(request, 'accounts/user_approval_list.html', {'pending_users': pending_users})


@login_required
@require_POST
@csrf_protect
def approve_user(request, user_id):
    """管理员批准用户（POST请求）"""
    if not request.user.is_superuser:
        messages.error(request, '只有管理员可以执行此操作')
        return redirect('accounts:index')

    try:
        user_profile = UserProfile.objects.get(user_id=user_id)
        user_profile.is_approved = True
        user_profile.save()
        messages.success(request, f'用户 {user_profile.user.username} 已批准')
    except UserProfile.DoesNotExist:
        messages.error(request, '用户不存在')

    return redirect('accounts:user_approval_list')