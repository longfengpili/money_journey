# 资金光环驾驶舱 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将家庭资金总览改为以真实资产结构驱动的浅色资金光环驾驶舱。

**Architecture:** 保留 Dashboard 的统计和筛选逻辑，调整首屏语义结构与资金光环样式；下方图表沿用现有 Chart.js，仅统一视觉节奏。所有持续动画由 CSS 驱动，不增加运行时依赖。

**Tech Stack:** React 19、TypeScript、CSS、Chart.js、Playwright。

**Spec:** [资金光环驾驶舱设计](../specs/2026-11-21-funds-halo.md)

## Global Constraints

- 默认只汇总存续中资产，历史状态单独说明。
- 类别名称、金额和占比来自真实接口，显示的占比合计为 100%。
- 保持极光玻璃浅色主题、手机布局、键盘操作与减少动态效果支持。
- 不复制 HaloFlux 的代码、图形或媒体。

## Review Focus

- 类别超过四项时，所有类别仍可点击且金额、百分比不溢出。
- 点击类别后，下方筛选和统计更新，光环其他类别保留为弱化状态。
- 空资产、游客数据和历史状态下仍显示正确口径。
- 390px 手机视口不产生横向滚动。
- 减少动态效果时不运行持续动画。

---

### Task 1: 资金光环与真实指标

**Files:** `frontend/src/features/dashboard/Dashboard.tsx`、`frontend/src/styles/dashboard-cockpit.css`、`tests/frontend/e2e/application.spec.ts`

- [x] 添加浏览器回归：光环显示总额、全部类别，点击后筛选联动。
- [x] 实现中心光环、类别微型面板与储蓄/非储蓄指标。
- [x] 构建并运行回归。

### Task 2: 全页动效与响应式

**Files:** `frontend/src/styles/dashboard-cockpit.css`、`frontend/src/features/dashboard/Dashboard.tsx`

- [x] 让首屏光束与下方图表、到期计划、成员区使用一致的低亮度光效。
- [x] 在手机端调整类别布局并限制持续动画；遵守减少动态效果设置。
- [x] 用桌面和手机浏览器检查溢出、可读性和交互。

### Task 3: 验证与本机测试页

**Files:** `README.md`、本计划

- [x] 更新总览说明，运行前端构建、单元测试和浏览器回归。
- [x] 仅重建本机 38000 测试 web 容器，核对游客与真实资产数据。
- [x] 记录验证结果；不自动提交或推送。

## 验证结果

- `npm run build` 通过；`npm run test` 通过，4 个单元测试成功；Prettier 和 `git diff --check` 通过。
- 38000 测试页的游客总览与资金光环筛选浏览器回归均通过，390px 手机布局无横向滚动。
- 后续金币动效回归覆盖首次筛选与再次恢复全量的文案、细光线固定方向、图表中心落点和三张图表的展开效果。
- 测试库登录用户当前资产汇总为 6 类，类别金额合计与总额 `3568066.31` 一致；本次未修改数据库。
