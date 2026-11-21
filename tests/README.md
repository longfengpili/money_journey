# 测试与验收

所有测试代码、测试专用设置和验收文档集中在顶层 `tests/`。业务实现与设计文档仍分别位于应用目录和 `docs/`。

```text
tests/
├── backend/                 # Django 回归，按业务模块分包
│   ├── accounts/
│   ├── analytics/
│   ├── funds/
│   ├── money_journey/
│   └── savings_calculator/
├── frontend/
│   ├── unit/                # 金额与 CSV 单元测试
│   ├── e2e/                 # Chrome 业务流程
│   └── tsconfig.json        # 测试类型检查与前端依赖解析
├── docs/                    # 实施计划、执行和验收记录
├── settings.py              # 独立内存数据库设置
└── artifacts/               # 本地测试产物，Git 和镜像构建忽略
```

## 后端

在仓库根目录，使用当前 Python 环境执行：

```bash
python manage.py test --settings=tests.settings
```

单独运行资金模块：

```bash
python manage.py test tests.backend.funds --settings=tests.settings
```

当前共 108 项测试。SQLite 跳过 2 项需要 MySQL 行锁或大额聚合精度特性的检查；完整验收需要在独立 MySQL 测试库运行。原来的应用标签（如 `manage.py test funds`）不再包含已迁移的测试，需改用 `tests.backend.funds`。

MySQL 验收须使用独立测试环境，并确认数据库连接和 `DATABASES['default']['TEST']['NAME']` 指向专用测试库。不要将服务器原业务库作为迁移试验或浏览器测试环境。

## 前端

依赖继续由 `frontend/package.json` 管理；在 `frontend/` 执行：

```bash
npm ci
npm test
npm run build
npm run format:check
```

`npm test` 先检查前端测试的 TypeScript 类型，再运行顶层 `tests/frontend/unit/` 的 3 项单元测试。Vitest 和 Playwright 的配置入口保留在 `frontend/`，指向顶层测试目录。

浏览器验收需要已运行的新版本独立测试站点、本机 Chrome 和隔离测试账号。在 PowerShell 中设置凭据文件后运行：

```powershell
$env:MJ_E2E_CREDENTIALS='本机隔离测试账号文件的绝对路径.json'
npm run test:e2e
```

默认访问 `http://127.0.0.1:38000`，可通过 `MJ_BASE_URL` 修改。账号文件包含 `member`、`manager`、`other` 和 `unassigned` 样例，各项字段为 `id`、`username`、`password`。当前共 10 组流程，缺少相应凭据时部分业务流程会跳过，不可据此宣称全部验收通过。测试会在隔离库新增或更新样例资产、账号和快照。

新截图和临时报告位于 `tests/artifacts/playwright/`。原有 `frontend/test-results/` 本地产物保留，没有清空；凭据、数据库备份、证书和私钥不得提交 Git。

## 验收记录

- [组件化前端执行与验收记录](docs/2026-11-21-component-frontend-progress.md)
- [测试目录整理计划与验证结果](docs/2026-11-21-test-layout-plan.md)
