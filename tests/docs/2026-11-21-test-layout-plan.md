# 测试目录统一实施计划

> 执行方式：使用 executing-plans 在当前工作区实施，不创建 worktree。

目标：将测试代码、测试专用设置和验收文档统一放到顶层 tests/，保留全部用例和既有测试命令。

依据：用户确认“测试代码和测试文档都统一”。采用 writing-plans 与 karpathy-guidelines，按现有行为验证目录迁移。

## 文件布局

- tests/backend/{accounts,analytics,funds,money_journey,savings_calculator}/：后端测试，目录作为 Python 包。
- tests/settings.py：独立 SQLite 测试设置。
- tests/frontend/unit/：金额与 CSV 单元测试。
- tests/frontend/e2e/：Chrome 业务回归。
- tests/docs/：实施与验收记录；tests/README.md 提供统一测试入口。
- frontend/{vitest,playwright}.config.ts：保留工具入口，指向顶层测试文件，依赖继续由 frontend/package.json 管理。

## 实施与验证

- [x] 移动后端测试与测试设置，调整内部导入、子进程工作目录和文档命令。
- [x] 移动前端测试，调整工具发现路径与依赖解析，保持 3 项单测和 10 组浏览器流程。
- [x] 移动执行验收记录并修复链接，补充统一测试说明。
- [x] SQLite 保持 108 项（2 跳过），MySQL 保持 108 项；前端单测、构建、格式与浏览器回归通过。
- [x] 复核所有移动均保留原文件内容和用例，提交本阶段改动，不自动推送。


## 验证结果

- 共移动 25 个文件：20 个 Python 测试模块、1 个测试设置、3 个前端测试文件和1份执行验收记录；新增包入口和统一测试说明。
- 迁移前后均为108个后端测试方法；除纯引擎子进程工作目录随层级适配外，所有测试方法AST一致。
- SQLite 108项完成（2项数据库特性跳过），新镜像内MySQL 108项全部通过。
- 顶层前端测试的类型检查、3项单测、构建和Prettier通过；Chrome 10组流程全部通过，新产物写入tests/artifacts/playwright。
- 正式多阶段镜像构建成功，独立测试容器已更新且healthy；没有访问服务器业务数据库。
- Python PEP 8、无待生成迁移、Git空白和移动后文档链接检查通过；独立只读审查无遗留问题。
- 已有README的LICENSE链接指向不存在文件，迁移前亦如此，未在此次目录整理中扩大修改。
- 本阶段在当前main保存独立提交，不自动推送；既有本地测试产物未清空。
