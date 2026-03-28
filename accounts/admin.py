from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from accounts.models import UserProfile


class UserProfileInline(admin.StackedInline):
    """在用户管理界面中显示用户资料"""
    model = UserProfile
    can_delete = False
    verbose_name = '用户资料'
    verbose_name_plural = '用户资料'
    fields = ('is_approved', 'created_at')
    readonly_fields = ('created_at',)


class CustomUserAdmin(UserAdmin):
    """自定义用户管理，包含批准状态"""
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_approved', 'is_active')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'userprofile__is_approved')

    def is_approved(self, obj):
        """获取用户的批准状态"""
        try:
            profile = obj.userprofile
            return profile.is_approved
        except UserProfile.DoesNotExist:
            return False
    is_approved.boolean = True
    is_approved.short_description = '已批准'


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """用户资料独立管理界面"""
    list_display = ('user', 'is_approved', 'created_at')
    list_filter = ('is_approved', 'created_at')
    search_fields = ('user__username', 'user__email')
    list_editable = ('is_approved',)
    readonly_fields = ('user', 'created_at')
    fields = ('user', 'is_approved', 'created_at')


# 取消默认的User注册，重新注册自定义的UserAdmin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)