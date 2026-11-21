import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";

type Actor = { id: number; username: string; password: string };
const fixturePath = process.env.MJ_E2E_CREDENTIALS;
const fixtures: Record<string, Actor> = fixturePath
  ? JSON.parse(readFileSync(fixturePath, "utf8"))
  : {};

test.beforeEach(async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  (page as unknown as { runtimeErrors: string[] }).runtimeErrors = errors;
});
test.afterEach(async ({ page }) => {
  expect(
    (page as unknown as { runtimeErrors: string[] }).runtimeErrors,
  ).toEqual([]);
});

async function signIn(page: import("@playwright/test").Page, actor: Actor) {
  await page.goto("/app/login");
  await page.getByLabel("用户名", { exact: true }).fill(actor.username);
  await page.getByLabel("密码", { exact: true }).fill(actor.password);
  await page.getByRole("button", { name: "登录", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "家庭资金总览" }),
  ).toBeVisible();
}

test("游客总览、图表与手机导航可用", async ({ page }) => {
  await page.goto("/app/");
  await expect(page).toHaveURL(/\/app\/$/);
  await expect(page.locator(".app-layout.glass-shell")).toBeVisible();
  await expect(page.locator(".dashboard-hero-side")).toContainText(
    "未来半年到期",
  );
  const navigation = page.getByRole("navigation", { name: "主要导航" });
  expect(await navigation.getByRole("link").allTextContents()).toEqual([
    "资金计算器",
    "资金总览",
  ]);
  await expect(page.getByRole("region", { name: "登录提示" })).toContainText(
    "当前展示演示数据",
  );
  await expect(
    page.getByRole("link", { name: "登录查看真实资产" }),
  ).toHaveAttribute("href", "/app/login");
  await page.getByRole("link", { name: "登录查看真实资产" }).click();
  await expect(
    page.getByRole("heading", { name: "登录家庭资金空间" }),
  ).toBeVisible();
  await page.goBack();
  await expect(
    page.getByRole("heading", { name: "家庭资金总览" }),
  ).toBeVisible();
  await expect(page.getByText("¥1,280,000.00", { exact: true })).toBeVisible();
  await expect(page.getByRole("img", { name: "银行资金分布" })).toBeVisible();
  await expect(page.getByRole("img", { name: "成员资产结构" })).toBeVisible();
  await expect(
    page.getByRole("img", { name: "未来半年到期金额" }),
  ).toBeVisible();
  await expect(
    page.getByRole("table", { name: "未来半年到期明细" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "资金快照历史趋势" }),
  ).toHaveCount(0);
  await page.screenshot({
    path: test.info().outputPath("dashboard-desktop.png"),
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect
    .poll(() =>
      page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth + 1,
      ),
    )
    .toBeTruthy();
  await expect
    .poll(() =>
      page
        .locator(".dashboard canvas")
        .evaluateAll((canvases) =>
          Math.max(
            ...canvases.map((canvas) =>
              Math.abs(
                (canvas as HTMLCanvasElement).width / devicePixelRatio -
                  canvas.getBoundingClientRect().width,
              ),
            ),
          ),
        ),
    )
    .toBeLessThan(2);
  await page.screenshot({
    path: test.info().outputPath("dashboard-mobile.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "切换导航" }).click();
  await page.getByRole("link", { name: "资金计算器", exact: true }).click();
  await expect(page.getByRole("heading", { name: "资金计算器" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "基本参数" })).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: test.info().outputPath("calculator-mobile.png"),
    fullPage: true,
  });
});

test("游客各页面使用统一极光玻璃主题", async ({ page }) => {
  for (const path of [
    "/app/",
    "/app/calculator",
    "/app/login",
    "/app/register",
  ]) {
    await page.goto(path);
    await expect(page.locator(".app-layout.glass-shell")).toBeVisible();
    const card = page.locator(".card").filter({ visible: true }).first();
    await expect(card).toBeVisible();
    await expect(card).toHaveCSS("color", "rgb(23, 37, 65)");
  }
});

test("游客计算、结果恢复、半年筛选与 CSV 导出", async ({ page }) => {
  await page.goto("/app/calculator");
  await page.getByLabel("活期保留金额（元）").fill("10000");
  await page.getByLabel("年度支出（元）", { exact: true }).fill("1200");
  await page.getByLabel("计算月数").fill("40");
  await page.getByRole("button", { name: "开始计算" }).click();
  await expect(page.getByText("¥217,840.00", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("columnheader", { name: "月支出", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("columnheader", { name: "年度支出月", exact: true }),
  ).toBeVisible();
  await page.reload();
  await expect(page.getByText("¥217,840.00", { exact: true })).toBeVisible();
  await page.getByLabel("明细月份范围").selectOption("half");
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "导出 CSV" }).click();
  expect((await download).suggestedFilename()).toContain(".csv");
  await page.getByLabel("计算月数").fill("41");
  await expect(
    page.getByRole("status").filter({ hasText: "参数已修改" }),
  ).toBeVisible();
});

test("成员新增编辑本人资产，其他人资产只读，手机没有页面溢出", async ({
  page,
}) => {
  test.skip(!fixtures.member, "需指定隔离测试库的 MJ_E2E_CREDENTIALS");
  await signIn(page, fixtures.member);
  await page.goto(`/app/funds?owner_id=${fixtures.other.id}`);
  await expect(page.getByText("仅查看", { exact: true }).first()).toBeVisible();
  const otherAssets = page.getByRole("region", { name: "非储蓄类资产" });
  const savingsAssets = page.getByRole("region", { name: "储蓄存款" });
  await expect(
    otherAssets.getByRole("columnheader", { name: "类别" }),
  ).toHaveCount(1);
  await expect(
    otherAssets.getByRole("columnheader", { name: "银行" }),
  ).toHaveCount(1);
  await expect(
    savingsAssets.getByRole("columnheader", { name: "类别" }),
  ).toHaveCount(0);
  await expect(
    savingsAssets.getByRole("columnheader", { name: "银行" }),
  ).toHaveCount(1);
  await expect(
    otherAssets.getByRole("columnheader", { name: "到期日" }),
  ).toHaveCount(0);
  await expect(
    savingsAssets.getByRole("columnheader", { name: "到期日" }),
  ).toHaveCount(1);
  const tableWidths = await page
    .locator(".asset-group .desktop-assets table")
    .evaluateAll((tables) =>
      tables.map((table) => table.getBoundingClientRect().width),
    );
  expect(tableWidths).toHaveLength(2);
  expect(tableWidths[0]).toBeCloseTo(tableWidths[1], 0);
  await expect(
    page.getByRole("button", { name: "编辑", exact: true }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "新增资产", exact: true }).click();
  await page.getByLabel("金额（元）", { exact: true }).fill("0");
  await page.getByRole("button", { name: "保存资产" }).click();
  await expect(
    page.getByRole("status").filter({ hasText: "资产已保存" }),
  ).toBeVisible();
  await page.goto(`/app/funds?owner_id=${fixtures.member.id}`);
  await page.getByRole("button", { name: "编辑", exact: true }).first().click();
  await page.getByLabel("金额（元）", { exact: true }).fill("25.26");
  await page.getByRole("button", { name: "保存资产" }).click();
  await expect(
    page.getByRole("status").filter({ hasText: "资产已保存" }),
  ).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.locator(".card-list")).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: test.info().outputPath("funds-mobile.png"),
    fullPage: true,
  });
});

test("管理员导入 CSV、刷新快照并创建不登录的成员", async ({ page }) => {
  test.skip(!fixtures.manager, "需指定隔离测试库的 MJ_E2E_CREDENTIALS");
  await signIn(page, fixtures.manager);
  await page.goto("/app/operations");
  await page.getByLabel("CSV 文件").setInputFiles({
    name: "browser.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(
      "bank,category,amount\nICBC,CURRENT,0.01\nICBC,CURRENT,-1\n",
    ),
  });
  await page.getByRole("button", { name: "上传并导入" }).click();
  await expect(
    page.getByRole("status").filter({ hasText: "成功导入 1 条" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "刷新当天快照" }).click();
  await expect(page.getByText(/快照已刷新/)).toBeVisible();
  await page.goto("/app/members");
  const username = "e2e_family_" + Date.now();
  await page.getByLabel("用户名", { exact: true }).fill(username);
  await page.getByLabel("姓名", { exact: true }).fill("浏览器家庭成员");
  await page.getByRole("button", { name: "创建家庭成员", exact: true }).click();
  await expect(
    page.getByRole("status").filter({ hasText: "家庭成员已创建" }),
  ).toBeVisible();
  await expect(
    page.getByRole("row").filter({ hasText: username }),
  ).toContainText("不登录的成员");
});

test("管理员可查看成员编辑与删除确认，资产按类别分区", async ({ page }) => {
  test.skip(!fixtures.manager || !fixtures.member, "需要隔离测试账号");
  await signIn(page, fixtures.manager);
  await page.goto("/app/members");
  const row = page
    .getByRole("row")
    .filter({ hasText: fixtures.member.username });
  await row.getByRole("button", { name: "编辑" }).click();
  const dialog = page.getByRole("dialog", { name: "编辑家庭成员" });
  const isCentered = () =>
    dialog.evaluate((element) => {
      const box = element.getBoundingClientRect();
      return (
        Math.abs(box.left - (innerWidth - box.width) / 2) < 2 &&
        Math.abs(box.top - (innerHeight - box.height) / 2) < 2
      );
    });
  expect(await isCentered()).toBeTruthy();
  await expect(dialog.getByLabel("启用账号")).toBeVisible();
  await expect(dialog.getByLabel("已批准")).toBeVisible();
  await expect(dialog.getByLabel("家庭管理员")).toBeVisible();
  await dialog.getByRole("button", { name: "删除成员" }).click();
  await expect(dialog.getByLabel("资产接收成员")).toBeVisible();
  await expect(dialog.getByRole("button", { name: "确认删除" })).toBeDisabled();
  await dialog
    .getByLabel("资产接收成员")
    .selectOption(String(fixtures.manager.id));
  await expect(dialog.getByRole("button", { name: "确认删除" })).toBeEnabled();
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await isCentered()).toBeTruthy();
  await dialog.getByRole("button", { name: "取消" }).last().click();
  await dialog.getByRole("button", { name: "关闭" }).click();
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/app/funds");
  await expect(page.getByRole("region", { name: "储蓄存款" })).toBeVisible();
  await expect(
    page.getByRole("region", { name: "非储蓄类资产" }),
  ).toBeVisible();
  await expect(
    page
      .getByRole("region", { name: "非储蓄类资产" })
      .getByRole("columnheader", { name: "更新时间" }),
  ).toBeVisible();
  await expect(
    page
      .getByRole("region", { name: "储蓄存款" })
      .getByRole("columnheader", { name: "年利率" }),
  ).toBeVisible();
});

test("注册账号等待批准，管理员批准后可登录", async ({ page }) => {
  test.skip(!fixtures.manager, "需指定隔离测试库的 MJ_E2E_CREDENTIALS");
  const username = "e2e_register_" + Date.now();
  const password = "Safe-long-password-963!";
  await page.goto("/app/register");
  await page.getByLabel("用户名", { exact: true }).fill(username);
  await page.getByLabel("姓名", { exact: true }).fill("待批准成员");
  await page.getByLabel("密码", { exact: true }).fill(password);
  await page.getByLabel("确认密码", { exact: true }).fill(password);
  await page.getByRole("button", { name: "提交注册" }).click();
  await expect(
    page.getByRole("status").filter({ hasText: "注册成功" }),
  ).toBeVisible();
  await page.goto("/app/login");
  await page.getByLabel("用户名", { exact: true }).fill(username);
  await page.getByLabel("密码", { exact: true }).fill(password);
  await page.getByRole("button", { name: "登录", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("尚未批准");
  await signIn(page, fixtures.manager);
  await page.goto("/app/members");
  await page
    .getByRole("row")
    .filter({ hasText: username })
    .getByRole("button", { name: "批准加入" })
    .click();
  await expect(
    page.getByRole("status").filter({ hasText: "账号已批准" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "退出", exact: true }).click();
  await signIn(page, { id: 0, username, password });
});

test("跨标签切换账号后旧草稿不能在新身份下重试", async ({ page }) => {
  test.skip(!fixtures.member, "需要隔离测试账号");
  await signIn(page, fixtures.member);
  await page.goto("/app/funds");
  await page.getByRole("button", { name: "新增资产", exact: true }).click();
  await page.getByLabel("金额（元）", { exact: true }).fill("7.77");
  const other = await page.context().newPage();
  await other.goto("/app/login");
  await other.getByRole("button", { name: "退出", exact: true }).click();
  await signIn(other, fixtures.manager);
  const before = (
    await (
      await other.request.get(`/api/v1/funds/?owner_id=${fixtures.manager.id}`)
    ).json()
  ).count;
  await page.getByRole("button", { name: "保存资产" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(page.locator(".topbar")).toContainText("验收管理员");
  const after = (
    await (
      await page.request.get(`/api/v1/funds/?owner_id=${fixtures.manager.id}`)
    ).json()
  ).count;
  expect(after).toBe(before);
  await other.close();
});

test("计算提交期间禁用参数，避免结果与显示参数不一致", async ({ page }) => {
  await page.goto("/app/calculator");
  await page.getByLabel("计算月数").fill("40");
  await page.route("**/api/v1/calculator/calculate/", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 800));
    await route.continue();
  });
  await page.getByRole("button", { name: "开始计算" }).click();
  await expect(page.getByLabel("计算月数")).toBeDisabled();
  await expect(page.getByRole("heading", { name: "月度明细" })).toBeVisible();
});

test("无归属历史资产必须由管理员明确选择所有者", async ({ page }) => {
  test.skip(!fixtures.unassigned, "需要隔离历史资产样例");
  await signIn(page, fixtures.manager);
  await page.goto(
    `/app/funds?owner=${fixtures.unassigned.username}&savings_status=WITHDRAWN`,
  );
  await page.getByRole("button", { name: "编辑", exact: true }).first().click();
  await expect(
    page.getByRole("combobox", { name: "所有者", exact: true }),
  ).toHaveValue("");
  await page.getByRole("button", { name: "保存资产" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.getByRole("button", { name: "关闭编辑" }).click();
});

test("旧书签跳转新页面，旧表单不再执行", async ({ page }) => {
  await page.goto("/legacy/");
  await expect(page).toHaveURL(/\/app\/$/);
  await expect(page.getByText("返回原版页面 ↗")).toHaveCount(0);
  await page.goto("/savings-calculator/results/");
  await expect(page).toHaveURL(/\/app\/calculator$/);
  const context = await (
    await page.request.get("/api/v1/auth/context/")
  ).json();
  const response = await page.request.post("/savings-calculator/calculate/", {
    form: { csrfmiddlewaretoken: context.csrf_token },
  });
  expect(response.status()).toBe(410);
  expect((await response.json()).code).toBe("LEGACY_ENDPOINT_RETIRED");
  const bookmark = await page.request.get("/funds/?bank=ICBC", {
    maxRedirects: 0,
  });
  expect(bookmark.status()).toBe(302);
  expect(bookmark.headers().location).toBe("/app/funds?bank=ICBC");
});

test("成员特殊名称只作为文字展示", async ({ page }) => {
  const name = '</script><script>alert("name")</script>&家人';
  let dialogs = 0;
  page.on("dialog", async (dialog) => {
    dialogs += 1;
    await dialog.dismiss();
  });
  await page.route("**/api/v1/analytics/summary/*", async (route) => {
    const response = await route.fetch();
    const payload = await response.json();
    payload.owner_summary[0].first_name = name;
    await route.fulfill({ response, json: payload });
  });
  await page.goto("/app/");
  await expect(page.getByRole("cell", { name, exact: true })).toBeVisible();
  expect(dialogs).toBe(0);
});
