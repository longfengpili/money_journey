# 组件化重构后的待确认删除清单

状态：仅列候选，未执行文件、目录或业务记录删除。用户确认后再统一修改。

## 旧页面相关候选

以下内容当前仍承担旧页面回退，暂时保留。只有确认终止旧页面支持，并同步调整路由和测试后才能删除。

| 对象 | 当前用途与删除前置条件 |
| --- | --- |
| templates/index.html、templates/base.html | /legacy/ 与旧页面布局；删除会使回退入口不可用 |
| accounts/templates/accounts/login.html、register.html、user_approval_list.html、create_member.html | 旧登录、注册、审批、成员创建；须先关闭对应旧页面入口 |
| funds/templates/funds/record_list.html、add_record.html、edit_record.html、upload_csv.html | 旧资产及 CSV 页面；须完成旧页面回退观察 |
| analytics/templates/analytics/index.html、dashboard.html、charts.html | 原分析页面；须明确保留的维护入口 |
| savings_calculator/templates/savings_calculator/calculator_input.html、calculator_results.html、calculator_input_loggedin.html、calculator_results_loggedin.html | 原计算器及历史遗留登录版模板；须逐一核对路由、导出与回退引用 |
| templates/registration/register.html、user_approval_list.html | 删除前核对 Django 默认认证视图是否引用，不按名称推断无用 |
| static/css/style.css、static/js/main.js | 原模板依赖，新 React 前端独立；须确认无旧页面引用 |
| funds/demorecord.py、analytics/demorecord.py | 原演示数据；analytics 新 API 仍复用 DEMO_DATA，因此当前不能直接删除 |

旧视图和路由不能整文件删除：accounts/views.py、funds/views.py、analytics/views.py、savings_calculator/views.py 仍有回退用途，CSV API 也仍复用原模板下载函数。若决定清理，应先分离下载逻辑，再逐项移除模板路由；权限、表单、查询、导入、快照、计算引擎、模型和迁移都需要继续保留。

## 本轮生成但可单独确认的本地文件

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

本清单不代表已经获得删除授权。旧页面清理与本次新前端交付分开处理。

## 本地旧构建哈希文件明细

仅列当前宿主构建未引用的本地文件，未删除；正式镜像由干净构建阶段生成，不依赖这些历史文件。

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
