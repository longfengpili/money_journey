# 单家庭资产归属与权限实施计划

> 执行要求：使用 superpowers:executing-plans 在当前会话逐项实施，以勾选框记录进度与验证结果。

**目标**：全家共享查看资产，普通成员仅维护本人资产，家庭管理员管理全家资产。

**架构**：沿用 Django 单体与现有 UserProfile、FundRecord。权限判定集中在账号应用，资金页面、CSV 与后台复用同一规则，所有权始终关联账号。

**技术栈**：现有 Python、Django、MySQL 与模板，不新增运行依赖。

**设计依据**：[单家庭资产归属与权限设计](../specs/2026-11-21-family-asset-permissions.md)。业务规则和实施计划均已在对话中确认。

## 全局约束

- 一个系统记录一个家庭，每个账号代表一个人，每位资产所有者都有账号。
- 普通成员只能新增、修改自己名下的资产。
- 家庭管理员可以代任何成员录入、修改资产，并调整归属。
- 资产所有者关联账号，录入人单独记录，展示名称从所有者账号获取。
- 文档和代码注释使用中文，Python 遵循 PEP 8。

## 重点核验

1. 缺少用户资料、未批准或停用的账号不能借直接请求写入资产。
2. 历史空归属、文本与账号冲突的记录不能被普通成员认领。
3. CSV bulk_create 绕过 save 时，仍正确填写所有者与录入人。
4. 家庭管理员编辑他人资产不改变录入人，省略所有者不改变原归属。
5. 普通 staff 用户通过后台表单、列表编辑或批量操作也不能修改他人资产或提升自身角色。

## 任务 1：角色和集中权限

文件：修改 accounts/models.py、accounts/admin.py、accounts/views.py、tests/backend/accounts/test_permissions.py；新增 accounts/permissions.py、accounts/migrations/0002_userprofile_is_family_admin.py。

接口：is_family_admin(user) -> bool；can_write_assets(user) -> bool；can_edit_record(user, record) -> bool。角色判定支持维护账号，写入要求账号有效且已批准，超级管理员沿用维护能力。普通成员必须满足 record.user_id == user.pk。

- [x] 先增加测试，覆盖本人、他人、空归属、家庭管理员、普通 staff、超级管理员、未批准和停用账号的权限矩阵。
- [x] 运行 accounts 测试，确认新增接口尚未实现导致预期失败。
- [x] 添加独立角色字段与迁移，实现上述权限函数。后台角色编辑只允许系统超级管理员，阻止 POST 伪造字段和用户资料内联修改。
- [x] 审批列表和审批操作使用家庭管理员判定，导航入口同步修改，防止后台修改资料或权限实现自我提权。
- [x] 运行 accounts 测试，确认权限矩阵通过。

## 任务 2：所有者、录入人与历史核对

文件：修改 funds/models.py、tests/backend/funds/test_ownership.py；新增 funds/migrations/0013_fundrecord_created_by.py、funds/management/commands/audit_asset_owners.py 及所需包初始化文件。

接口：FundRecord.created_by 为可空账号外键，on_delete=SET_NULL；FundRecord.owner_display 返回关联账号的 first_name 或 username，历史空归属时回退文本；manage.py audit_asset_owners 默认只读输出记录 ID、账号和文本的匹配状态。

- [x] 先增加回归测试，验证账号改名后的显示、历史空归属的显示、录入人未知、所有者与录入人独立及核对命令零写入。
- [x] 运行 funds 测试，确认预期失败后增加字段、展示属性与核对命令。
- [x] 核对命令提供显式 --apply，仅补齐空关联且 owner 精确匹配唯一用户名的记录，事务内重查归属，重复执行结果一致。空文本和无法匹配的记录输出待处理，已有账号关联保持权威。
- [x] 测试核对命令的默认只读、精确匹配补齐、冲突保留、重复执行，并确认历史录入人保持空值。

## 任务 3：资金页面、CSV 与后台统一写入规则

文件：修改 funds/views.py、funds/admin.py、tests/backend/funds/test_ownership.py、funds/templates/funds/add_record.html、edit_record.html、record_list.html、upload_csv.html。

接口：资金页面与后台调用任务 1 权限函数；所有者解析集中为 funds/permissions.py 中 resolve_record_owner(actor, username, current_owner=None) -> User，权限错误抛 PermissionDenied，未知用户名产生可展示的校验错误。

- [x] 先增加请求测试，普通成员伪造所有者被拒绝、家庭管理员转移归属成功、管理员编辑省略 owner 保留原用户、编辑保留 created_by。
- [x] 增加 CSV 上传测试，混合本人和他人行时按现有逐行反馈行为处理，合法行所有者和 created_by 正确；未知用户名不产生记录。
- [x] 增加后台回归测试，覆盖对象编辑、list_editable、普通 staff 的批量删除、归属下拉选择和未批准账号，确认受保护目标不可修改。
- [x] 运行测试确认预期失败，再接入统一权限和所有者解析，创建记录与 CSV 写入设置 created_by，后台新增明确填写 user 并按操作者限制选择。
- [x] 所有者只读展示从账号获取，编辑按钮由同一权限判定控制，管理员选项支持家庭管理员角色。
- [x] 运行 funds 测试，所有入口权限矩阵通过。

## 任务 4：管理员创建暂不登录的成员

文件：新增 accounts/forms.py、accounts/templates/accounts/create_member.html；修改 accounts/views.py、accounts/urls.py、tests/backend/accounts/test_permissions.py、templates/base.html。

接口：CreateMemberForm 接收 username、first_name；create_member(request) 仅允许已批准家庭管理员或维护账号访问，事务内创建 User 与 UserProfile，账号使用不可用密码且已批准。

- [x] 先测试管理员成功创建、普通成员直接 POST 被拒绝、重复用户名、资料写入失败事务回滚，以及伪造 is_staff/is_superuser/is_family_admin 不生效。
- [x] 运行测试确认预期失败，再实现表单、页面、路由与导航，保留原注册流程。
- [x] 验证新成员可以作为资产所有者被选中，has_usable_password() 为 False，普通成员无法授予家庭管理员角色。

## 任务 5：汇总兼容与整体验证

文件：修改 analytics/views.py、tests/backend/analytics/test_family_totals.py 及相关展示模板；按需更新 README.md 中的权限说明。

- [x] 增加同家庭共享查询测试，以及账号改名后的所有者筛选、汇总和图表测试，覆盖历史空关联记录的回退显示。
- [x] 将实时归属汇总改为按 user 主键分组，展示账号姓名；兼容现有 owner 筛选参数，避免用户名变更后资产拆成多组。历史快照保留历史展示含义。
- [x] 在当前 Conda normal 环境核验 Python 与依赖。数据库测试使用隔离测试数据库，记录实际环境和结果。
- [x] 运行 python manage.py test tests.backend --settings=tests.settings，确认关键业务回归通过。
- [x] 运行 python manage.py makemigrations --check --dry-run、python manage.py check、git diff --check，处理本次改动产生的问题。
- [ ] 真实数据库归属核对与部署迁移：已尝试加载本地环境配置执行只读核对，数据库连接返回 OperationalError，尚未获得真实数据核对结果。
- [x] 更新计划中的完成项、阻碍和验证证据，交付代码差异、管理员配置方式及历史数据待核对项。

## 交付状态

- 任务 1 至 4 已完成，任务 5 的代码与隔离测试已完成。
- 分支为 `codex/family-asset-permissions`，工作保留在当前目录。
- 实际数据库迁移与历史归属核对待数据库连接恢复后进行。应用迁移成功后再启动新版服务，随后核对归属，明确结果后按需运行补齐。

## 验证记录

- 基线为 3 项测试通过。
- 权限接口缺失与字段缺失先产生预期失败，随后补齐角色和权限实现。
- CSV 活期导入失败定位为现有 start_date 未初始化，修复后通过。
- 账号改名测试先出现所有者汇总 3 组而预期 2 组，按账号归属汇总后通过。
- 后台越权编辑、列表编辑、批量删除，以及账号自我提权测试通过。
- 成员创建失败事务回滚、重复用户名、伪造权限字段、不可用密码测试通过。
- 游客演示所有者丢失先由测试复现，添加兼容显示后通过。
- 独立审查发现逐资产权限查询导致 N+1 查询。查询数量测试先失败，改为列表请求预计算权限后通过。
- 最终全套测试 21/21 通过，normal Python 3.10 / Django 4.2.16 与项目 Python 3.14 / Django 6.0.3 均通过。
- Django check 与 makemigrations --check --dry-run 通过，差异与新增 Python 文件样式检查通过。
- 后台列表同页包含他人资产时保存本人状态的正向测试先失败，跳过未修改表单的写入权限检查后通过。

## 实施判断

- Ruling: 在当前目录的新分支实施，保留计划与已有工作 — 工作区初始仅有本轮设计文档，当前目录在可写范围内 — 代码差异与主目录共享，交付时注明分支。
- Ruling: 增加内存数据库测试配置与可配置日志目录 — 现有日志目录固定为 Linux 路径导致 Windows 测试无法启动 — 运维若使用自定义日志路径需设置 DJANGO_LOG_DIR，Docker 默认目录仍为 /app/logs。
- Ruling: 补齐 CSV 起始日期初始化 — 权限验证所需的正常活期导入触发旧代码错误 — 额外覆盖一个既有导入缺陷。
- Ruling: 使用现有 normal 环境测试并额外验证项目 Django 6 环境 — normal 的 Django 为 4.2，项目环境缺少 crontab 和 whitenoise，额外运行通过进程内 sys.path 使用 normal 环境的这两个纯 Python 包 — 未安装或升级环境依赖，生产 MySQL 验证仍待连接恢复。
- 独立审查没有其他确定的 Critical/Important 问题，没有确定的待处理 Minor。

## 2026-11-21 容器部署验证

- 用户要求部署本次容器并测试。本机 8000 端口已由其他项目使用，测试入口设为 `http://127.0.0.1:38000/`。
- 使用独立 Compose 项目 `money_journey_test`，Web 容器为 `money_journey_web_test`，数据库容器为 `money_journey_db_test`，MySQL 数据存放在该项目独立卷内。
- 测试环境与构建覆盖配置保存在本次会话的本地可视化目录。凭据使用新生成的测试值。
- 官方基础镜像下载缓慢，改用本机已有镜像的系统依赖重新生成运行镜像。构建阶段以 scratch 为起点复制系统文件，排除旧 app 目录，再复制本次源代码及启动脚本。
- 运行依赖为 Python 3.11.15、Django 5.2.12、MySQL 8.0.45，其余 Python 包与 requirements/production.txt 的固定版本一致。
- 增加 .dockerignore，新镜像已验证不含 `/app/.env` 和 `/app/.git`。
- 启动脚本自动完成独立测试库全部迁移，`migrate --check` 及 `check` 均通过。
- 在容器独立 MySQL 回归数据库运行 21 项测试全部通过，使用 --keepdb 保留测试数据库。
- 真实 HTTP 冒烟测试 55 项检查通过，包含实际登录与 CSRF、家庭管理员创建成员、本人及他人资产写入限制、归属调整、CSV、共享读取、图表页面、静态资源及 12 个月储蓄计算。
- 宿主机访问首页返回 200，健康检查返回 healthy，Docker 健康状态为 healthy。
- 容器启动日志曾通过 crontab show 回显数据库连接信息。已将启动展示改为任务数量，重建后验证测试数据库密码未出现在新容器日志中。
- 只读核对测试库的样例资产归属通过。原有业务数据库的迁移和历史核对仍需在该数据库恢复连接后完成。
- 测试账号和样例资产保留在独立测试库，运行中的测试容器保留供用户访问。
- 用户反馈审批页的用户资料入口有问题。复现为旧 `/admin/records/userprofile/` 链接，已改用 Django 命名路由，并将系统账号管理按钮限定为超级管理员可见，家庭管理员可使用创建成员入口。实际 HTTP 验证后台链接均返回 200，容器 MySQL 上 23 项回归测试全部通过，容器已更新且健康。
