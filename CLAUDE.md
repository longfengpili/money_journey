# Claude项目指南

本文档为Claude AI助手提供项目上下文和开发指南，帮助Claude更好地理解和维护"Money Journey"项目。

## 📋 项目概述

**Money Journey** 是一个基于Django的个人资金管理与追踪系统。用户可以通过后台录入资金记录，前端展示按所有者、银行等分类的资金总额和图表分析。

### 核心功能
- **资金记录管理**：银行、所有者、类别、金额、利率、存期（年）、到期日等字段
- **智能分类展示**：活期存款单独表格，定期存款完整信息表格
- **自动利息计算**：金额 × 利率 × 存期（年） ÷ 100
- **数据汇总展示**：按所有者、银行、类别、储蓄状态汇总（仅ACTIVE状态）
- **图表可视化**：使用Chart.js展示资金分布（仅ACTIVE状态）
- **用户认证与批准系统**：新用户需要管理员批准，超级管理员直接登录
- **权限控制**：管理员显示批准页面链接，普通用户不显示
- **后台管理**：Django Admin，支持用户批准状态管理
- **批量数据导入**：CSV文件上传，智能数据映射和验证
- **CSV模板下载**：提供标准格式模板文件
- **定时任务系统**：自动检测到期存款（未来7天内到期），发送PushPlus通知，定期清理旧记录（3年前）
- **日志系统**：结构化日志记录，支持info、warning、error级别，每日日志文件分割
- **健康检查端点**：容器健康检查端点 `/health/`，支持Docker健康检查
- **快照创建判断**：防止重复创建每日快照，确保每天只创建一个快照
- **安全性增强**：record_list登录要求修复，CSV上传行数限制（最大10,000行）和文件大小限制（10MB）
- **储蓄计算器**：家庭财务规划工具，模拟逐月现金流，支持3年定期存款模拟、年龄段收支配置、数据导出（CSV/Excel/PDF），游客/登录双模式

### 技术栈
- **后端**: Django 6.0.3
- **数据库**: MySQL 8.0
- **前端**: HTML/CSS, Bootstrap 5, Chart.js
- **认证**: Django内置认证系统
- **定时任务**: django-crontab
- **通知服务**: PushPlus
- **日志系统**: Python logging + 文件处理
- **容器化**: Docker + Docker Compose + Gunicorn

## 🏗️ 项目结构

```
money_journey/
├── manage.py                          # Django管理脚本
├── requirements.txt                    # Python依赖包
├── .env.example                       # 环境变量示例文件
├── .env                               # 环境变量文件（本地配置，不提交）
├── Dockerfile                         # Docker镜像构建文件
├── docker-compose.yml                 # Docker Compose开发环境配置
├── docker-compose.prod.yml            # Docker Compose生产环境配置
├── CLAUDE.md                          # Claude AI助手项目指南
├── DEPLOYMENT.md                      # 部署文档
├── docker/                            # Docker相关配置目录
├── money_journey/                     # 主项目配置
│   ├── __init__.py
│   ├── settings/                      # 配置分离目录（base.py, production.py）
│   │   ├── __init__.py
│   │   ├── base.py                    # 基础配置（开发环境）
│   │   └── production.py              # 生产环境配置
│   ├── notification.py                # PushPlus通知服务
│   ├── urls.py                        # URL路由配置
│   ├── wsgi.py
│   └── asgi.py
├── funds/                             # 资金记录管理应用（原records）
│   ├── __init__.py
│   ├── admin.py                       # 后台管理配置
│   ├── apps.py
│   ├── models.py                      # FundRecord数据模型定义
│   ├── views.py                       # 视图函数（仪表板、记录列表、图表、CSV导入等）
│   ├── urls.py                        # 应用URL路由
│   └── templates/funds/               # 资金记录相关模板
│       ├── add_record.html            # 添加记录表单模板
│       ├── edit_record.html           # 编辑记录表单模板
│       ├── record_list.html           # 资金记录列表模板（含活期/定期分离展示）
│       └── upload_csv.html            # CSV上传模板
├── accounts/                          # 用户账户与认证应用
│   ├── __init__.py
│   ├── admin.py                       # 用户管理后台配置
│   ├── apps.py
│   ├── models.py                      # UserProfile扩展模型
│   ├── views.py                       # 用户认证与批准视图
│   ├── urls.py                        # 认证相关URL路由
│   └── templates/accounts/            # 用户认证相关模板
│       ├── login.html                 # 登录页面
│       ├── register.html              # 用户注册页面
│       └── user_approval_list.html    # 管理员批准用户页面
├── analytics/                         # 数据分析与定时任务应用
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   └── tasks.py                         # 定时任务：到期存款检测、旧记录清理
├── savings_calculator/                 # 储蓄计算器应用
│   ├── __init__.py
│   ├── apps.py
│   ├── calculator.py                    # 计算引擎：逐月现金流模拟
│   ├── forms.py                         # 表单：基本参数、年龄段参数
│   ├── views.py                         # 视图：游客/登录双模式输入与结果展示
│   ├── urls.py                          # 应用URL路由
│   └── templates/savings_calculator/    # 储蓄计算器相关模板
│       ├── calculator_input.html        # 游客模式输入表单
│       ├── calculator_input_loggedin.html  # 登录模式输入表单
│       ├── calculator_results.html      # 游客模式计算结果
│       └── calculator_results_loggedin.html  # 登录模式计算结果
├── templates/                         # 全局模板目录
│   ├── base.html                      # 基础模板（含导航栏、权限控制）
│   └── registration/                  # 认证相关模板（兼容旧路径）
│       ├── login.html                 # 登录页面（兼容旧路径）
│       ├── register.html              # 用户注册页面（兼容旧路径）
│       └── user_approval_list.html    # 管理员批准用户页面（兼容旧路径）
├── static/                            # 静态文件目录
│   ├── css/style.css                  # 自定义样式
│   └── js/main.js                     # JavaScript文件
├── staticfiles/                       # 收集的静态文件（生产环境）
├── log/                                # 应用日志目录（info.log, error.log, daily.log）
├── requirements/                      # 依赖包分离目录
│   ├── base.txt                       # 基础依赖
│   ├── dev.txt                        # 开发环境依赖
│   └── prod.txt                       # 生产环境依赖
└── venv/                              # Python虚拟环境（不提交）
```

## 🔧 关键文件说明

### 1. 项目配置
- **money_journey/settings/base.py** - 基础配置，包含MySQL数据库配置、语言时区设置、静态文件配置、认证设置、定时任务配置、日志配置等
- **money_journey/settings/production.py** - 生产环境配置，继承base.py，覆盖安全设置
- **money_journey/urls.py** - 主URL路由，包含funds应用路由和认证路由
- **money_journey/notification.py** - PushPlus通知服务，用于定时任务发送到期提醒

### 2. 数据层
- **funds/models.py** - `FundRecord`模型定义，包含所有资金记录字段和选择项；`FundSnapshot`快照模型，用于每日资金快照
- **funds/admin.py** - Django Admin配置，自定义显示和过滤选项

### 3. 业务逻辑
- **funds/views.py** - 视图函数，包括仪表板、记录列表、图表视图、用户认证与批准、CSV批量导入、记录添加/编辑、快照创建
- **funds/urls.py** - 应用URL路由配置，包含所有功能端点

### 4. 定时任务与日志系统
- **analytics/tasks.py** - 定时任务：`check_outdated_records`检测到期存款（未来7天内到期），`clean_old_records`清理旧记录（3年前）
- **money_journey/settings/base.py** - 日志配置：结构化日志记录，支持不同级别，日志文件分割
- **money_journey/settings/base.py** - 定时任务配置：django-crontab配置，每日19-21点执行到期检测
- **log/** - 日志目录：info.log（信息日志），error.log（错误日志），daily.log（每日日志）

### 5. 前端展示
- **templates/base.html** - 基础模板，使用Bootstrap 5，包含导航栏
- **funds/templates/funds/dashboard.html** - 仪表板模板，展示汇总数据
- **funds/templates/funds/charts.html** - 图表模板，集成Chart.js
- **static/css/style.css** - 自定义样式文件
- **static/js/main.js** - JavaScript文件
- **static/js/toast-messages.js** - Toast消息提示组件，用于显示操作反馈

## 📊 数据模型详解

### FundRecord模型字段
| 字段名 | 类型 | 描述 | 备注 |
|--------|------|------|------|
| bank | CharField | 银行 | 使用BANK_CHOICES选项 |
| owner | CharField | 所有者 | 自由文本，最大长度100 |
| category | CharField | 类别 | 使用CATEGORY_CHOICES选项 |
| savings_status | CharField | 储蓄状态 | 使用SAVINGS_STATUS_CHOICES，默认'ACTIVE' |
| amount | DecimalField | 金额 | max_digits=15, decimal_places=2，必须为正数 |
| interest_rate | DecimalField | 利率 | 百分比，可为空 |
| deposit_period | IntegerField | 存期 | 单位为年，可为空 |
| interest_amount | 属性方法 | 计算利息 | 金额 × 利率 × 存期（年） ÷ 100，自动计算 |
| due_date | DateField | 到期日 | 可为空 |
| due_month | CharField | 到期月 | YYYY-MM格式，可为空 |
| created_at | DateTimeField | 创建时间 | 自动设置当前时间 |
| updated_at | DateTimeField | 更新时间 | 自动更新 |

### 选择项定义
```python
# 银行选择项
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

# 类别选择项
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

# 储蓄状态选择项
SAVINGS_STATUS_CHOICES = [
    ('ACTIVE', '存续中'),
    ('MATURED', '已到期'),
    ('WITHDRAWN', '已取出'),
    ('ROLLED_OVER', '已续存'),
]
```

## 🚀 开发指南

### 数据库操作
1. **生成迁移文件**：`python manage.py makemigrations`
2. **应用迁移**：`python manage.py migrate`
3. **创建超级用户**：`python manage.py createsuperuser`

### 运行开发服务器
```bash
# 激活虚拟环境
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# 运行服务器
python manage.py runserver
```

### 访问地址
- 开发服务器：http://localhost:8000/
- 后台管理：http://localhost:8000/admin/

### 默认认证信息
- 用户名：`admin`
- 密码：`Admin123!`

## 🎨 前端开发指南

### 模板继承
所有页面模板都继承自`templates/base.html`：
```html
{% extends 'base.html' %}
{% block title %}页面标题{% endblock %}
{% block content %}
<!-- 页面内容 -->
{% endblock %}
```

### 静态文件引用
```html
{% load static %}
<link rel="stylesheet" href="{% static 'css/style.css' %}">
<script src="{% static 'js/main.js' %}"></script>
```

### 数据格式化
使用Django模板过滤器格式化数据：
```html
{{ total_amount|intcomma }}  <!-- 千位分隔符 -->
{{ record.created_at|date:"Y-m-d H:i" }}  <!-- 日期格式化 -->
{{ record.get_bank_display }}  <!-- 获取选择项的显示值 -->
```

### Chart.js集成
图表页面使用Chart.js，通过`extra_js`块引入：
```html
{% block extra_js %}
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
// Chart.js初始化代码
</script>
{% endblock %}
```

## 🔍 代码规范

### Python代码
- 遵循PEP 8规范
- 使用4空格缩进
- 导入顺序：标准库、第三方库、本地应用
- 模型字段按逻辑分组，使用fieldsets
- 视图函数添加适当的装饰器（如`@login_required`）

### 模板代码
- 使用双花括号`{{ }}`输出变量
- 使用`{% %}`标签控制逻辑
- 保持模板简洁，复杂逻辑放在视图中
- 使用Bootstrap类进行样式设计

### 静态文件
- CSS使用Bootstrap为主，自定义样式为辅
- JavaScript代码放在`static/js/main.js`中
- 第三方库使用CDN引入

## 🧪 测试指南

### 运行测试
```bash
python manage.py test
```

### 测试数据
测试时应创建以下类型的数据：
1. 不同所有者的记录
2. 不同银行的记录
3. 不同类别的记录
4. 不同储蓄状态的记录
5. 不同金额范围的记录

### 验证功能
1. 后台管理：添加、编辑、删除记录
2. 前端展示：验证汇总计算正确性
3. 图表功能：验证图表数据准确性
4. 用户认证：登录、注销、权限控制

## 🔄 数据库迁移

### 新增字段
1. 在`models.py`中添加字段
2. 生成迁移文件：`python manage.py makemigrations`
3. 应用迁移：`python manage.py migrate`

### 修改字段
1. 修改`models.py`中的字段定义
2. 生成迁移文件
3. 应用迁移
4. 注意：修改已有字段类型可能导致数据丢失

### 删除字段
1. 从`models.py`中删除字段
2. 生成迁移文件
3. 应用迁移
4. 注意：删除字段会永久删除该字段的数据

## ⚠️ 注意事项

### 数据库配置
- 生产环境使用环境变量存储数据库密码
- 定期备份数据库
- 使用UTF-8mb4字符集支持中文

### 安全性
- 生产环境设置`DEBUG = False`
- 配置`ALLOWED_HOSTS`
- 使用HTTPS
- 定期更新依赖包

### 性能优化
- 数据库查询使用`select_related`和`prefetch_related`
- 添加适当的数据库索引
- 使用缓存机制
- 静态文件使用CDN

## 📈 扩展功能建议

### 短期改进（部分已实现✅）
1. ✅ 数据导入/导出功能（CSV、Excel）- 已实现CSV批量导入和模板下载
2. ✅ 定时任务系统 - 已实现到期存款检测、旧记录清理、PushPlus通知
3. ✅ 日志系统 - 已实现结构化日志记录、日志文件分割
4. ✅ 健康检查端点 - 已实现`/health/`端点，支持容器健康检查
5. ✅ 快照创建判断 - 已实现防止重复创建每日快照
6. ✅ 安全性增强 - 已修复record_list登录要求，添加CSV上传限制
7. 搜索和过滤功能
8. 分页功能
9. ✅ 数据验证增强 - 已实现表单验证、CSV数据验证、用户输入验证

### 中期功能
1. 报表生成（PDF、Excel）
2. ✅ 邮件提醒（到期提醒）- 已实现PushPlus通知服务，支持到期存款提醒
3. 多语言支持
4. API接口

### 长期规划
1. 移动端应用
2. 数据同步功能
3. 高级分析功能
4. 团队协作功能

## 🆘 故障排除

### 常见问题

#### 数据库连接失败
- 检查MySQL服务状态
- 验证数据库配置（用户名、密码、数据库名）
- 检查网络连接

#### 静态文件未加载
- 检查`STATICFILES_DIRS`设置
- 运行`python manage.py collectstatic`
- 检查文件权限

#### 迁移失败
- 检查模型定义是否正确
- 删除迁移文件重新生成
- 检查数据库连接

#### 模板渲染错误
- 检查模板语法
- 验证视图传递的上下文变量
- 检查模板文件路径

### 调试技巧
1. 使用`print()`语句调试视图
2. 检查Django日志
3. 使用Django Debug Toolbar
4. 查看浏览器开发者工具控制台

## 🤝 与Claude协作指南

### 代码修改流程
1. 先阅读相关文件，理解现有代码结构
2. 修改前备份重要文件
3. 修改后测试功能是否正常
4. 更新相关文档
5. 更新README.md

### 新功能开发
1. 先设计数据模型
2. 实现后台管理
3. 创建视图函数
4. 开发前端模板
5. 测试完整功能

### 问题修复
1. 重现问题
2. 定位问题原因
3. 实施修复
4. 验证修复效果
5. 添加测试用例

---

**最后更新**：2026-04-04（已更新反映最新功能：储蓄计算器、游客/登录双模式、数据导出、UI优化等）
**维护者**：Claude AI助手
**项目状态**：开发完成，可运行