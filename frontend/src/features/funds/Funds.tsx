import { useState } from "react";
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
export default function Funds() {
  const [params, setParams] = useSearchParams();
  const [version, setVersion] = useState(0);
  const [editor, setEditor] = useState<Asset | "new" | null>(null);
  const [notice, setNotice] = useState("");
  const options = useResource<FundOptions>("/funds/options/");
  const state = useResource<Page>("/funds/?" + params.toString(), version);
  const turnPage = (value: number) => {
    const next = new URLSearchParams(params);
    next.set("page", String(value));
    setParams(next);
  };
  if (options.loading) return <Loading />;
  if (!options.data) return <ErrorNotice error={options.error} />;
  const page = state.data;
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
      <ErrorNotice error={state.error} />
      {state.error && (
        <Button onClick={() => setVersion(version + 1)}>重新读取</Button>
      )}
      {state.loading ? (
        <Loading />
      ) : (
        page && (
          <section className="card">
            <div
              className="actions"
              style={{ justifyContent: "space-between", marginBottom: 20 }}
            >
              <h2 style={{ margin: 0 }}>共 {page.count} 条记录</h2>
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
            <div className="table-wrap desktop-assets">
              <table>
                <thead>
                  <tr>
                    <th>所有者</th>
                    <th>银行 / 类别</th>
                    <th>状态</th>
                    <th>到期日</th>
                    <th className="money">金额</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {page.results.map((asset) => (
                    <tr key={asset.id}>
                      <td className="break">{asset.owner_display}</td>
                      <td>
                        {asset.bank_display}
                        <div className="muted">{asset.category_display}</div>
                      </td>
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
                      <td>{asset.due_date || "—"}</td>
                      <td className="money">¥{money(asset.amount)}</td>
                      <td>{edit(asset)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="card-list">
              {page.results.map((asset) => (
                <article className="asset-mobile" key={asset.id}>
                  <header>
                    <div>
                      <strong>{asset.owner_display}</strong>
                      <div className="label">
                        {asset.bank_display} · {asset.category_display}
                      </div>
                    </div>
                    <strong>¥{money(asset.amount)}</strong>
                  </header>
                  <div className="actions">
                    <span className="badge">{asset.status_display}</span>
                    <span className="label">
                      {asset.due_date || "无到期日"}
                    </span>
                    {edit(asset)}
                  </div>
                </article>
              ))}
            </div>
            {!page.results.length && (
              <div className="empty">暂无符合筛选的资产</div>
            )}
            <footer className="pagination">
              <span className="label">
                第 {page.page} 页 · 每页 {page.page_size} 条
              </span>
              <div className="actions">
                <Button
                  disabled={page.page <= 1}
                  onClick={() => turnPage(page.page - 1)}
                >
                  上一页
                </Button>
                <Button
                  disabled={page.page * page.page_size >= page.count}
                  onClick={() => turnPage(page.page + 1)}
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
