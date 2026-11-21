import { useState, type ReactNode } from "react";
import { useSearchParams } from "react-router-dom";
import { useResource } from "../../lib/resource";
import { money } from "../../lib/money";
import type { Asset, FundOptions } from "../../lib/types";
import { Button, ErrorNotice, Loading, PageTitle } from "../../components/ui";
import Filters from "../../components/Filters";
import AssetEditor from "./AssetEditor";

type Page = {
  count: number;
  page: number;
  page_size: number;
  results: Asset[];
};

const updatedAtFormatter = new Intl.DateTimeFormat("zh-CN", {
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

function formatUpdatedAt(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : updatedAtFormatter.format(date);
}

function AssetGroup({
  title,
  assets,
  edit,
  savings,
}: {
  title: string;
  assets: Asset[];
  edit: (asset: Asset) => ReactNode;
  savings: boolean;
}) {
  return (
    <section className="asset-group" aria-label={title}>
      <h3>
        {title}{" "}
        <span className="label">
          {savings ? "本页" : "共"} {assets.length} 条
        </span>
      </h3>
      <div className="table-wrap desktop-assets">
        <table>
          <thead>
            <tr>
              <th>所有者</th>
              {!savings && <th>类别</th>}
              <th>银行</th>
              <th>状态</th>
              {savings && <th>年利率</th>}
              {savings && <th>存期</th>}
              {savings && <th>到期日</th>}
              {!savings && <th>更新时间</th>}
              <th className="money">金额</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {assets.map((asset) => (
              <tr key={asset.id}>
                <td className="break">{asset.owner_display}</td>
                {!savings && <td>{asset.category_display}</td>}
                <td>{asset.bank_display}</td>
                <td>
                  <span
                    className={
                      asset.savings_status === "ACTIVE"
                        ? "badge"
                        : "badge muted"
                    }
                  >
                    {asset.status_display}
                  </span>
                </td>
                {savings && (
                  <td>
                    {asset.interest_rate === null
                      ? "—"
                      : `${asset.interest_rate}%`}
                  </td>
                )}
                {savings && (
                  <td>
                    {asset.deposit_period ? `${asset.deposit_period} 年` : "—"}
                  </td>
                )}
                {savings && <td>{asset.due_date || "—"}</td>}
                {!savings && (
                  <td>
                    <time dateTime={asset.updated_at}>
                      {formatUpdatedAt(asset.updated_at)}
                    </time>
                  </td>
                )}
                <td className="money">¥{money(asset.amount)}</td>
                <td>{edit(asset)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="card-list">
        {assets.map((asset) => (
          <article className="asset-mobile" key={asset.id}>
            <header>
              <div>
                <strong>{asset.owner_display}</strong>
                <div className="label">
                  {savings
                    ? asset.bank_display
                    : `${asset.category_display} · ${asset.bank_display}`}
                </div>
              </div>
              <strong>¥{money(asset.amount)}</strong>
            </header>
            <div className="actions">
              <span className="badge">{asset.status_display}</span>
              {savings && (
                <span className="label">
                  利率{" "}
                  {asset.interest_rate === null
                    ? "—"
                    : `${asset.interest_rate}%`}{" "}
                  · 存期{" "}
                  {asset.deposit_period ? `${asset.deposit_period} 年` : "—"}
                </span>
              )}
              {savings && (
                <span className="label">{asset.due_date || "无到期日"}</span>
              )}
              {!savings && (
                <span className="label">
                  更新于 {formatUpdatedAt(asset.updated_at)}
                </span>
              )}
              {edit(asset)}
            </div>
          </article>
        ))}
      </div>
      {!assets.length && <div className="empty">暂无{title}记录</div>}
    </section>
  );
}

export default function Funds() {
  const [params, setParams] = useSearchParams();
  const [version, setVersion] = useState(0);
  const [editor, setEditor] = useState<Asset | "new" | null>(null);
  const [notice, setNotice] = useState("");
  const options = useResource<FundOptions>("/funds/options/");
  const nonSavingsParams = new URLSearchParams(params);
  nonSavingsParams.delete("page");
  nonSavingsParams.set("category_group", "non_savings");
  const savingsParams = new URLSearchParams(params);
  savingsParams.set("category_group", "savings");
  const nonSavingsState = useResource<Page>(
    "/funds/?" + nonSavingsParams.toString(),
    version,
  );
  const savingsState = useResource<Page>(
    "/funds/?" + savingsParams.toString(),
    version,
  );
  const turnPage = (value: number) => {
    const next = new URLSearchParams(params);
    next.set("page", String(value));
    setParams(next);
  };
  if (options.loading) return <Loading />;
  if (!options.data) return <ErrorNotice error={options.error} />;
  const nonSavings = nonSavingsState.data;
  const savingsPage = savingsState.data;
  const error = nonSavingsState.error || savingsState.error;
  const edit = (asset: Asset) =>
    asset.can_edit ? (
      <Button onClick={() => setEditor(asset)}>编辑</Button>
    ) : (
      <span className="muted">仅查看</span>
    );
  return (
    <>
      <PageTitle
        title="资产记录"
        detail="全家共享查看，每一笔资产都有清楚的归属。"
        actions={
          <Button
            className="primary"
            onClick={() => {
              setNotice("");
              setEditor("new");
            }}
          >
            新增资产
          </Button>
        }
      />
      {notice && (
        <div className="notice success" role="status">
          {notice}
        </div>
      )}
      <Filters
        params={params}
        onChange={setParams}
        owners={options.data.members}
        banks={options.data.bank_choices}
        categories={options.data.category_choices}
        statuses={options.data.status_choices}
      />
      <ErrorNotice error={error} />
      {error && (
        <Button onClick={() => setVersion(version + 1)}>重新读取</Button>
      )}
      {nonSavingsState.loading || savingsState.loading ? (
        <Loading />
      ) : (
        nonSavings &&
        savingsPage && (
          <section className="card">
            <div
              className="actions"
              style={{ justifyContent: "space-between", marginBottom: 20 }}
            >
              <h2 style={{ margin: 0 }}>
                共 {nonSavings.count + savingsPage.count} 条记录
              </h2>
              <select
                aria-label="资产排序"
                style={{ width: "auto" }}
                value={params.get("ordering") || "-amount"}
                onChange={(event) => {
                  const next = new URLSearchParams(params);
                  next.set("ordering", event.target.value);
                  next.delete("page");
                  setParams(next);
                }}
              >
                <option value="-amount">金额从高到低</option>
                <option value="amount">金额从低到高</option>
                <option value="due_date">到期日从早到晚</option>
              </select>
            </div>
            <AssetGroup
              title="非储蓄类资产"
              savings={false}
              assets={nonSavings.results}
              edit={edit}
            />
            <AssetGroup
              title="储蓄存款"
              savings
              assets={savingsPage.results}
              edit={edit}
            />
            <footer className="pagination">
              <span className="label">
                储蓄存款 · 第 {savingsPage.page} 页 · 每页{" "}
                {savingsPage.page_size} 条
              </span>
              <div className="actions">
                <Button
                  disabled={savingsPage.page <= 1}
                  onClick={() => turnPage(savingsPage.page - 1)}
                >
                  上一页
                </Button>
                <Button
                  disabled={
                    savingsPage.page * savingsPage.page_size >=
                    savingsPage.count
                  }
                  onClick={() => turnPage(savingsPage.page + 1)}
                >
                  下一页
                </Button>
              </div>
            </footer>
          </section>
        )
      )}
      {editor && (
        <AssetEditor
          asset={editor === "new" ? undefined : editor}
          options={options.data}
          onClose={() => setEditor(null)}
          onSaved={() => {
            setEditor(null);
            setNotice("资产已保存");
            setVersion(version + 1);
          }}
        />
      )}
    </>
  );
}
