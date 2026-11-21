# 组件化重构后的删除清单与执行记录

状态：用户于 2026-11-21 确认删除，已按下列具体路径执行文件清理；业务数据、数据库卷与 Git 历史保留。

## 旧页面相关候选

以下为批准时的对象与前置条件。执行时已终止旧模板支持，旧 GET/HEAD 地址保留查询参数并跳转新页面，旧提交入口返回 410 且不执行写入。

| 对象 | 批准时的用途与删除前置条件 |
| --- | --- |
| templates/index.html、templates/base.html | /legacy/ 与旧页面布局；删除会使回退入口不可用 |
| accounts/templates/accounts/login.html、register.html、user_approval_list.html、create_member.html | 旧登录、注册、审批、成员创建；须先关闭对应旧页面入口 |
| funds/templates/funds/record_list.html、add_record.html、edit_record.html、upload_csv.html | 旧资产及 CSV 页面；须完成旧页面回退观察 |
| analytics/templates/analytics/index.html、dashboard.html、charts.html | 原分析页面；须明确保留的维护入口 |
| savings_calculator/templates/savings_calculator/calculator_input.html、calculator_results.html、calculator_input_loggedin.html、calculator_results_loggedin.html | 原计算器及历史遗留登录版模板；须逐一核对路由、导出与回退引用 |
| templates/registration/register.html、user_approval_list.html | 删除前核对 Django 默认认证视图是否引用，不按名称推断无用 |
| static/css/style.css、static/js/main.js | 原模板依赖，新 React 前端独立；须确认无旧页面引用 |
| funds/demorecord.py、analytics/demorecord.py | 原演示数据；analytics 新 API 仍复用 DEMO_DATA，因此当前不能直接删除 |

旧视图和路由保留文件，仅改为兼容跳转：accounts/views.py、funds/views.py、analytics/views.py、savings_calculator/views.py 已不再渲染旧模板；CSV API 改用 funds/csv_template.py，游客演示改用 analytics/demo.py，原演示模块已删除；权限、表单、查询、导入、快照、计算引擎、模型和迁移都需要继续保留。

## 一并确认并清理的本地文件

| 路径 | 说明 |
| --- | --- |
| frontend/AGENTS.md | BoardUI CLI 自动生成的厂商指导文件，已 Git 忽略；项目规则与用户授权仍优先 |
| frontend/.cursor/rules/boardui.mdc | CLI 自动生成的编辑器规则，已 Git 忽略 |
| frontend/src/utils/use-dismiss-on-outside-press.ts | CLI 基础工具，本轮未使用；未来引入弹层组件可能复用 |
| frontend/dist/assets/ 中旧构建哈希文件 | 构建设置保留旧文件，避免未经批准清空目录；清理前须依据当前 dist/index.html 和回退版本逐项列出文件 |

## 不属于删除候选

- frontend/node_modules、测试结果和会话产物为本地构建或验证数据，本轮不清空。
- 原业务数据库和 MySQL 数据卷不删除。
- 独立测试库中验收账号与样例保留，不在用户未指定具体记录前自动清理。
- Git 开发分支、提交历史和 Docker 缓存保留，不自动清理。

本次操作依据用户对本清单的“确认删除”；未扩展到未列出的文件或目录。

## 本地旧构建哈希文件明细

执行前逐项检查宿主 dist/index.html 未引用以下 10 个文件后删除。正式镜像由干净构建阶段生成，不依赖这些历史文件。其后新产生的构建哈希文件不在本次删除范围内。

- `frontend/dist/assets/index-B08BlP1z.css`
- `frontend/dist/assets/index-B2GyIYsr.js`
- `frontend/dist/assets/index-BIXLjUEf.js`
- `frontend/dist/assets/index-Bt-RsBYk.js`
- `frontend/dist/assets/index-BW4lRsGw.js`
- `frontend/dist/assets/index-CdH59elj.js`
- `frontend/dist/assets/index-CTOKB6l_.js`
- `frontend/dist/assets/index-DbvzHx46.js`
- `frontend/dist/assets/index-Jl7lV3xH.css`
- `frontend/dist/assets/index-P6dJY0bL.js`

## 2026-11-21 执行记录

- 共删除 36 个明确列出的文件，包括 23 个旧页面/静态/演示文件、3 个 CLI 生成文件和 10 个已列名的旧构建资源。没有递归清空目录。
- 保留四个旧 views.py 与原 URL 名称；书签跳转新页面，旧写入返回 LEGACY_ENDPOINT_RETIRED。旧 CSV 下载地址跳转新 API，沿用新 API 的访问权限。
- 移除 FRONTEND_ENABLED 开关及侧栏旧版链接；默认首页固定进入 /app/，Django Admin 继续保留。
- 原权限、输入校验、共享统计、快照与计算器集成测试迁到新 API；补充旧入口无副作用和浏览器名称转义检查。
- 没有修改模型、迁移、数据库业务记录或数据库卷。未合并 main 或推送远程。

- 旧提交仍受 Django CSRF 校验：安全凭证缺失或过期时先返回 403；通过校验后返回 410，均不执行旧业务写入。

- 验证：SQLite 108 项（2 跳过）、MySQL 108 项全部通过，前端 3 项单测/类型构建/格式与 Chrome 10 组流程通过；独立审查无遗留问题。测试容器已更新。
