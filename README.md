# Money Journey - 资金旅程管理应用

![Django](https://img.shields.io/badge/Django-6.0.3-green)
![Python](https://img.shields.io/badge/Python-3.13-blue)
![MySQL](https://img.shields.io/badge/MySQL-8.0-orange)

一个基于Django的个人资金管理与追踪系统，帮助您记录、分析和管理资金旅程，轻松掌握财务状况。

## 🎯 功能特性

### 📝 资金记录管理
- 记录银行存款、理财产品、基金、股票等各类资金信息
- 支持银行、所有者、类别、储蓄状态等多维度分类
- 记录金额、利率、存期（年）、到期日等详细信息
- **智能分类展示**：活期存款单独显示，定期存款显示完整信息
- **自动利息计算**：金额 × 利率 × 存期（年） ÷ 100

### 📊 数据分析与展示
- **仪表板**：按所有者、银行、类别、储蓄状态汇总资金总额（仅显示ACTIVE状态记录）
- **资金记录列表**：智能分类显示 - 活期存款单独表格（简化显示），定期存款完整信息表格
- **图表分析**：使用Chart.js可视化展示资金分布（仅显示ACTIVE状态记录）
  - 按所有者资金分布（饼图）
  - 按银行资金分布（柱状图）
  - 按类别资金分布（环形图）

### 🔐 用户认证与权限管理
- Django内置认证系统
- **用户批准机制**：新注册用户需要管理员批准才能登录
- **权限分级**：超级管理员无需批准，可管理所有用户和数据
- **管理员界面**：管理员可查看待批准用户列表并批准
- **CSRF保护**：安全表单处理，防止跨站请求伪造攻击
- **安全注销**：POST请求注销，确保操作安全

### 👨‍💼 后台管理
- 完整的Django Admin界面
- 支持资金记录的数据录入、编辑、删除
- **用户批准管理**：在后台管理界面管理用户批准状态
- **批量数据导入**：支持CSV文件批量导入资金记录
- **CSV模板下载**：提供标准格式的CSV模板文件
- 自定义列表显示、过滤器和搜索功能

## 🏗️ 技术栈

- **后端框架**：Django 6.0.3
- **数据库**：MySQL 8.0
- **前端**：Bootstrap 5 + Chart.js
- **认证系统**：Django内置认证
- **部署**：开发环境

## 🚀 快速开始

### 环境要求

- Python 3.13+
- MySQL 8.0+
- Docker（可选，用于MySQL容器）

### 1. 克隆项目

```bash
git clone <repository-url>
cd wealth_journey
```

### 2. 设置虚拟环境

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置数据库

#### 使用本地MySQL
```sql
-- 创建数据库
CREATE DATABASE money_journey CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 创建用户（如果不存在）
CREATE USER 'longfengpili'@'localhost' IDENTIFIED BY '123456abc';
GRANT ALL PRIVILEGES ON money_journey.* TO 'longfengpili'@'localhost';
FLUSH PRIVILEGES;
```

#### 使用Docker MySQL
```bash
docker run --name money-journey-mysql \
  -e MYSQL_ROOT_PASSWORD=rootpassword \
  -e MYSQL_DATABASE=money_journey \
  -e MYSQL_USER=longfengpili \
  -e MYSQL_PASSWORD=123456abc \
  -p 3306:3306 \
  -d mysql:8.0
```

### 5. 数据库迁移

```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. 创建超级用户

```bash
python manage.py createsuperuser
```

### 7. 运行开发服务器

```bash
python manage.py runserver
```

## 📱 访问应用

### 开发服务器
- **应用首页**：http://localhost:8000/
- **后台管理**：http://localhost:8000/admin/

### 默认登录凭证
- **用户名**：`admin`
- **密码**：`Admin123!`

## 📁 项目结构

```
money_journey/
├── manage.py                          # Django管理脚本
├── requirements.txt                    # Python依赖包
├── money_journey/                      # 主项目配置
│   ├── settings.py                    # 项目配置（已配置MySQL）
│   ├── urls.py                        # URL路由配置
│   └── ...
├── records/                           # 主要应用
│   ├── models.py                      # FundRecord数据模型
│   ├── admin.py                       # 后台管理配置
│   ├── views.py                       # 视图函数
│   ├── urls.py                        # 应用路由
│   └── templates/records/             # 应用模板
│       ├── index.html                  # 首页模板
│       ├── dashboard.html              # 仪表板模板
│       ├── record_list.html            # 资金记录列表模板（含活期/定期分离）
│       ├── charts.html                 # 图表分析模板
│       ├── add_record.html             # 添加记录表单模板
│       ├── edit_record.html            # 编辑记录表单模板
│       ├── upload_csv.html             # CSV上传模板
│       └── ...
├── templates/                         # 全局模板
│   ├── base.html                      # 基础模板（含导航栏、权限控制）
│   └── registration/                  # 认证相关模板
│       ├── login.html                 # 登录页面
│       ├── register.html              # 用户注册页面
│       └── user_approval_list.html    # 管理员批准用户页面
└── static/                            # 静态文件
    ├── css/style.css                  # 自定义样式
    └── js/main.js                     # JavaScript文件
```

## 🗄️ 数据模型

### FundRecord（资金记录）
| 字段 | 类型 | 描述 | 可选值 |
|------|------|------|--------|
| bank | CharField | 银行 | 工商银行、建设银行等11个选项 |
| owner | CharField | 所有者 | 自定义名称 |
| category | CharField | 类别 | 储蓄存款、定期存款等8个选项 |
| savings_status | CharField | 储蓄状态 | 存续中、已到期、已取出、已续存 |
| amount | DecimalField | 金额 | 正数 |
| interest_rate | DecimalField | 利率 | 百分比（可选） |
| deposit_period | IntegerField | 存期 | 单位为年（可选） |
| interest_amount | 属性方法 | 计算利息 | 金额 × 利率 × 存期（年） ÷ 100 |
| due_date | DateField | 到期日 | YYYY-MM-DD格式（可选） |
| due_month | CharField | 到期月 | YYYY-MM格式（可选） |
| created_at | DateTimeField | 创建时间 | 自动生成 |
| updated_at | DateTimeField | 更新时间 | 自动更新 |

## 🔧 管理命令

### 创建超级用户
```bash
python manage.py createsuperuser
```

### 数据库迁移
```bash
# 生成迁移文件
python manage.py makemigrations

# 应用迁移
python manage.py migrate
```

### 检查项目配置
```bash
python manage.py check
```

### 运行测试
```bash
python manage.py test
```

## 🌐 前端页面

### 1. 首页 (`/`)
- 应用介绍和导航
- 登录/注册入口

### 2. 仪表板 (`/dashboard/`)
- **数据筛选**：仅显示ACTIVE状态的资金记录
- **资金总览**：显示所有活跃记录的资金总额
- **多维度汇总**：按所有者、银行、类别、储蓄状态汇总资金总额和记录数
- **格式优化**：金额和记录数列右对齐显示，提升可读性

### 3. 资金记录列表 (`/records/`)
- **智能分类展示**：活期存款单独表格（简化显示：所有者、银行、金额、状态、操作）
- **完整信息展示**：定期存款完整表格（所有者、银行、类别、金额、利率、存期、到期日、状态、利息、操作）
- **数据格式优化**：金额、利率、存期、利息列右对齐显示，提升可读性
- **自动利息计算**：基于金额、利率、存期自动计算并显示利息
- **编辑功能**：每条记录提供编辑按钮，可直接修改
- **添加记录**：提供添加新记录按钮

### 4. 图表分析 (`/charts/`)
- **数据筛选**：基于ACTIVE状态记录生成图表
- **可视化展示**：使用Chart.js展示资金分布
- **图表类型**：所有者分布（饼图）、银行分布（柱状图）、类别分布（环形图）
- **实时数据**：图表基于最新数据动态生成
- 使用Chart.js生成图表

## 🔒 安全注意事项

1. **生产环境配置**
   - 修改`SECRET_KEY`
   - 设置`DEBUG = False`
   - 配置`ALLOWED_HOSTS`
   - 使用环境变量存储数据库密码

2. **数据库安全**
   - 使用强密码
   - 限制数据库用户权限
   - 定期备份数据

3. **用户认证**
   - 使用Django内置认证系统
   - 密码哈希存储
   - CSRF保护

## 📈 数据展示示例

### 仪表板显示
- 总资金：¥1,234,567
- 所有者A：¥500,000（3条记录）
- 工商银行：¥300,000（2条记录）
- 储蓄存款：¥400,000（4条记录）
- 存续中：¥800,000（6条记录）

### 图表显示
- 饼图：不同所有者的资金占比
- 柱状图：各银行的资金分布
- 环形图：各类别的资金构成

## 🐛 故障排除

### 数据库连接失败
1. 检查MySQL服务是否运行
2. 验证数据库用户名和密码
3. 确认数据库名是否正确
4. 检查网络连接

### 静态文件未加载
1. 检查`STATICFILES_DIRS`设置
2. 运行`python manage.py collectstatic`
3. 确认Nginx/Apache配置（生产环境）

### 迁移失败
1. 删除迁移文件并重新生成
```bash
rm -rf records/migrations/0001_initial.py
python manage.py makemigrations
python manage.py migrate
```

## 🤝 贡献指南

1. Fork项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

## 📄 许可证

本项目采用MIT许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 👥 作者

- **longfengpili** - 项目创建者

## 🙏 致谢

- Django项目团队
- Bootstrap团队
- Chart.js团队
- 所有贡献者和用户

## 📞 支持

如有问题或建议，请提交Issue或联系维护者。

---

**注意**：本应用为开发版本，生产环境部署前请进行充分测试和安全配置。