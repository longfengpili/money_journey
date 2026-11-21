# Money Journey - 资金旅程管理应用

![Django](https://img.shields.io/badge/Django-5.2-green)
![Python](https://img.shields.io/badge/Python-3.10+-blue)
![MySQL](https://img.shields.io/badge/MySQL-8.0-orange)
![Docker](https://img.shields.io/badge/Docker-支持-2496ED)

基于 Django 与 React 的家庭资金管理系统，每个账号代表一个人，家庭成员共享查看资产，按角色管理归属与操作。

## 组件化前端

默认首页进入 `/app/`。游客可查看演示版资金总览并使用资金计算器；登录后可访问资产列表与编辑、CSV 与快照，家庭管理员还可审批成员。前端使用 React、TypeScript、Vite、Tailwind CSS 和 BoardUI 免费组件；后端通过 `/api/v1/` 提供 JSON，金额使用十进制字符串。

本地前端在 `frontend/` 执行 `npm ci`、`npm run dev`，访问 `http://127.0.0.1:5173/app/`。默认代理 Django 开发端口 8000，可用 `MJ_BACKEND_URL` 指定其他后端。类型与构建检查为 `npm run build`，逻辑测试为 `npm test`，真实浏览器流程为 `npm run test:e2e`；浏览器测试账号通过 `MJ_E2E_CREDENTIALS` 指定的本地 JSON 文件提供，不提交凭据。

生产镜像自动构建前端，静态资源由 Django/WhiteNoise 同域提供，继续使用 Session + CSRF。已确认退役旧页面，旧书签跳转到对应新页面，旧表单提交返回 410；不再支持 `FRONTEND_ENABLED` 首页回退。旧提交仍受 Django CSRF 校验：安全凭证缺失或过期时先返回 403；通过校验后返回 410，均不执行旧业务写入。部署与 HTTPS 要求见 [部署指南](DEPLOYMENT.md)。

各阶段进度见 [执行记录](tests/docs/2026-11-21-component-frontend-progress.md)，旧文件清理记录见 [删除清单](docs/superpowers/plans/2026-11-21-frontend-deletion-candidates.md)。

## 🎯 功能特性

### 📝 资金记录管理
- 记录银行存款、理财产品、基金、股票等各类资金信息
- 支持银行、所有者、类别、储蓄状态等多维度分类
- 记录金额、利率、存期（年）、到期日等详细信息
- **分类展示**：资产记录按储蓄存款与非储蓄类资产分区，储蓄存款显示利率和存期
- **自动利息计算**：金额 × 利率 × 存期（年） ÷ 100
- **统一录入校验**：页面和 CSV 共用字段校验，金额允许为零并精确保存两位小数；利率非负，存期填写时为正整数
- **导入反馈**：错误行展示行号和字段，合法行统一事务写入；文件超限或数据库写入失败时整份回滚，下载模板可直接用于导入

### 📊 数据分析与展示
- **仪表板**：按所有者、银行、类别、储蓄状态汇总资金总额，默认 ACTIVE，可组合筛选或选择全部状态
- **统一统计**：仪表板和图表页共用资产汇总规则，各维度金额与数量来自同一次分组查询，金额计算使用 Decimal
- **历史趋势**：每日 ACTIVE 快照仅跟随所有者筛选，关联账号改名后仍可查询历史，空关联历史保留原名称匹配
- **图表数据**：使用标准 JSON 传递，成员显示名称中的引号及脚本标签保持普通文本
- **资金记录列表**：按 `SAVINGS` 类别与其他类别分区，保留统一筛选、排序和分页
- **图表分析**：使用Chart.js可视化展示资金分布（仅显示ACTIVE状态记录）
  - 按所有者资金分布（饼图）
  - 按银行资金分布（柱状图）
  - 按类别资金分布（环形图）

### 🔐 用户认证与权限管理
- Django内置认证系统
- **用户批准机制**：新注册用户需要管理员批准才能登录
- **家庭共享**：每个账号代表一个人，登录成员可以查看全家的资产、汇总和资金计算器
- **资产修改权限**：普通成员仅能新增、修改自己名下的资产，家庭管理员可以管理全部资产并调整归属
- **管理员界面**：家庭管理员可以审批、创建和编辑成员；移除成员时指定资产接收人，原账号停用并保留历史快照
- **系统维护**：超级管理员通过后台的用户资料配置“家庭管理员”，家庭角色独立于后台登录权限
- **CSRF保护**：安全表单处理，防止跨站请求伪造攻击
- **安全注销**：POST请求注销，确保操作安全

### 👨‍💼 后台管理
- 完整的Django Admin界面
- 支持资金记录的数据录入、编辑、删除
- **用户批准管理**：在后台管理界面管理用户批准状态
- **批量数据导入**：支持CSV文件批量导入资金记录
- **CSV模板下载**：提供标准格式的CSV模板文件
- 自定义列表显示、过滤器和搜索功能

### 🧮 资金计算器
- **家庭财务规划**：模拟家庭月度现金流，覆盖数十年时间跨度
- **年龄分段收支**：支持配置多个年龄段的月收入和月支出
- **3年定期存款模拟**：自动将超出阈值的余额存入3年定期，到期自动转存（含利息）
- **年度支出扣减**：支持指定月份扣除年度一次性支出
- **逐月结果展示**：输出每月资金总额、活期余额、定期累计、到期转存、收支明细
- **数据导出**：支持CSV、Excel、PDF导出及打印
- **筛选功能**：支持"只看每年12月"快速筛选
- **游客/登录双模式**：游客可直接使用，登录用户有独立入口
- **独立计算引擎**：起始月份、初始活期及存款由外部明确传入，引擎可脱离 Django 运行，同一实例重复计算保持一致

### ⚙️ 系统运维与监控
- **定时任务系统**：自动检测到期存款（未来7天内到期），发送PushPlus通知，历史记录检查报告长期未更新的结束状态记录
- **日志系统**：结构化日志记录，支持info、warning、error级别，每日日志文件分割
- **健康检查端点**：容器健康检查端点 `/health/`，支持Docker健康检查
- **当天快照刷新**：家庭管理员可更新当天在册成员快照，按成员和日期唯一；移除成员后保留历史快照，刷新当天快照时清零其旧归属金额
- **安全性增强**：record_list登录要求修复，CSV上传行数限制（最大10,000行）和文件大小限制（10MB）

## 🏗️ 技术栈

- **后端框架**：Django 5.2 + Django REST framework
- **数据库**：MySQL 8.0
- **前端**：React 19 + TypeScript + Vite + Tailwind CSS v4 + BoardUI 免费基础 + Chart.js；旧模板保留 Bootstrap
- **认证系统**：Django内置认证
- **容器化**：Docker + Docker Compose
- **配置管理**：环境变量 + 配置分离（开发/生产）
- **部署**：支持开发环境、生产环境Docker部署
- **定时任务**：django-crontab
- **通知服务**：PushPlus
- **日志系统**：Python logging + 文件处理
- **应用服务器**：Gunicorn

## 🚀 快速开始

### 资产权限升级

部署本次更新时先执行 `python manage.py migrate`，增加家庭管理员与资产录入人字段。
系统维护人员在后台用户资料中为相应成员勾选“已批准”和“家庭管理员”。
家庭管理员登录后可在导航栏选择“创建家庭成员”，新成员账号使用不可用密码，日后需要登录时由系统维护人员设置密码。

运行 `python manage.py audit_asset_owners` 只读核对历史资产归属。
核对结果中的“文本冲突”以关联账号为实际所有者，“待核对”需要家庭管理员在资产编辑页面明确指定所有者。
核实用户名对应关系后，可执行 `python manage.py audit_asset_owners --apply`，仅补齐用户名精确匹配的空关联，支持重复执行。
已有资产的录入人保持未知，新录入及 CSV 导入会记录实际操作者。
实时所有者名称从关联账号读取，历史快照保留原有展示信息。

### 快照刷新升级

执行 `python manage.py audit_snapshots` 可只读核对重复用户日快照、空关联快照及 ACTIVE 空归属资产。
迁移增加用户与日期唯一约束，已有重复行会得到明确提示，需要根据核对结果处理后再执行迁移。
家庭管理员在资金列表中点击“刷新当天快照”，会更新全部成员的当天 ACTIVE 汇总，并记录最近生成者和刷新时间。
银行和类别汇总金额以两位小数字符串精确保存，历史数值格式继续支持读取。
`clean_old_records()` 现在只读报告最后更新超过 1095 天且状态为已取出或已续存的候选数量，记录保留在原表。

测试代码与验收文档统一位于顶层 [tests/](tests/README.md)。后端使用独立内存数据库，命令为 `python manage.py test --settings=tests.settings`；单模块测试使用 `tests.backend.模块名` 标签。
日志目录可通过 `DJANGO_LOG_DIR` 指定，默认位于项目的 `logs` 目录。

### 环境要求

#### 传统部署（无Docker）
- Python 3.13+
- MySQL 8.0+

#### Docker部署（推荐）
- Docker 20.10+
- Docker Compose 2.20+
- MySQL 8.0+（可使用容器化MySQL或外部数据库）

> **详细部署指南**：本项目支持完整的Docker化部署，包含开发和生产环境配置。请参阅 [DEPLOYMENT.md](DEPLOYMENT.md) 获取完整的Docker部署说明。

### 1. 克隆项目

```bash
git clone git@github.com:longfengpili/money_journey.git
cd money_journey
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
│   └── tasks.py                         # 定时任务：到期存款检测、历史记录只读检查
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

## 🗄️ 数据模型

### FundRecord（资金记录）
| 字段 | 类型 | 描述 | 可选值 |
|------|------|------|--------|
| bank | CharField | 银行 | 工商银行、建设银行、农业银行、农商银行、中国银行、招商银行、中信银行、浦发银行、兴业银行、民生银行、平安银行、支付宝、微信支付、公积金、股票、其他银行（共16个选项） |
| owner | CharField | 所有者 | 自定义名称，最大长度100 |
| category | CharField | 类别 | 活期存款、储蓄存款、定期存款、理财产品、基金、股票、债券、保险、其他（共9个选项） |
| savings_status | CharField | 储蓄状态 | 存续中、已到期、已取出、已续存（共4个选项） |
| amount | DecimalField | 金额 | 正数，max_digits=15, decimal_places=2 |
| interest_rate | DecimalField | 利率 | 百分比（可选），decimal_places=2 |
| deposit_period | IntegerField | 存期 | 单位为年（可选） |
| interest_amount | 属性方法 | 计算利息 | 金额 × 利率 × 存期（年） ÷ 100，自动计算 |
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
python manage.py test --settings=tests.settings
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

### 3. 资金记录列表 (`/funds/`)
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

### 5. 储蓄计算器 (`/savings-calculator/`)
- **输入表单**：配置父母/子女出生年份、月收支阈值、3年定期利率、年度支出、计算月数
- **年龄段参数**：动态添加/删除年龄段，每个年龄段配置月收入和月支出
- **计算结果**：逐月展示资金总额、活期余额、定期累计、到期转存、月储蓄、月收支
- **汇总统计**：最终资金总额、累计定期存款、净收入等关键指标
- **游客模式**：`/savings-calculator/` 无需登录即可使用
- **登录模式**：`/savings-calculator/loggedin/` 登录用户专属入口

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
# 删除所有应用的迁移文件（谨慎操作，备份数据）
rm -rf funds/migrations/0*.py
rm -rf accounts/migrations/0*.py
rm -rf analytics/migrations/0*.py
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

**最后更新**：2026-04-04（已更新反映最新功能：储蓄计算器、游客/登录双模式、数据导出、UI优化等）
**注意**：本应用为开发版本，生产环境部署前请进行充分测试和安全配置。
