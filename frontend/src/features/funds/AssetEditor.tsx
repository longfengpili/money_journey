import { useEffect, useRef, useState } from "react";
import { api, jsonBody } from "../../lib/api";
import { useSession } from "../../app/session";
import type { Asset, FundOptions } from "../../lib/types";
import { Button, ErrorNotice, FormErrors, Field } from "../../components/ui";

export default function AssetEditor({
  asset,
  options,
  onClose,
  onSaved,
}: {
  asset?: Asset;
  options: FundOptions;
  onClose: () => void;
  onSaved: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const { session } = useSession();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error>();
  useEffect(() => {
    const dialog = ref.current!;
    dialog.showModal();
    return () => dialog.close();
  }, []);
  return (
    <dialog
      ref={ref}
      aria-labelledby="asset-editor-title"
      onCancel={(event) => {
        event.preventDefault();
        if (!busy) onClose();
      }}
    >
      <div className="card">
        <header className="dialog-head">
          <h2 id="asset-editor-title">{asset ? "编辑资产" : "新增资产"}</h2>
          <Button aria-label="关闭编辑" disabled={busy} onClick={onClose}>
            关闭
          </Button>
        </header>
        <ErrorNotice error={error} />
        <FormErrors error={error}>
          <form
            onSubmit={async (event) => {
              event.preventDefault();
              setBusy(true);
              setError(undefined);
              const data = Object.fromEntries(
                new FormData(event.currentTarget),
              );
              try {
                await api(asset ? `/funds/${asset.id}/` : "/funds/", {
                  ...jsonBody(data),
                  method: asset ? "PATCH" : "POST",
                });
                onSaved();
              } catch (e) {
                setError(e as Error);
              } finally {
                setBusy(false);
              }
            }}
          >
            <div className="form-grid">
              <Field label="所有者">
                <select
                  name="owner_id"
                  required
                  defaultValue={
                    asset ? (asset.user_id ?? "") : (session.user?.id ?? "")
                  }
                >
                  <option value="">请选择成员</option>
                  {options.owners.map((member) => (
                    <option key={member.id} value={member.id}>
                      {member.first_name || member.username}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="银行">
                <select name="bank" defaultValue={asset?.bank ?? "ICBC"}>
                  {options.bank_choices.map(([code, label]) => (
                    <option key={code} value={code}>
                      {label}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="类别">
                <select
                  name="category"
                  defaultValue={asset?.category ?? "CURRENT"}
                >
                  {options.category_choices.map(([code, label]) => (
                    <option key={code} value={code}>
                      {label}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="状态">
                <select
                  name="savings_status"
                  defaultValue={asset?.savings_status ?? "ACTIVE"}
                >
                  {options.status_choices.map(([code, label]) => (
                    <option key={code} value={code}>
                      {label}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="金额（元）">
                <input
                  name="amount"
                  type="number"
                  min="0"
                  step="0.01"
                  required
                  defaultValue={asset?.amount ?? ""}
                />
              </Field>
              <Field label="年利率（%）">
                <input
                  name="interest_rate"
                  type="number"
                  min="0"
                  step="0.01"
                  defaultValue={asset?.interest_rate ?? ""}
                />
              </Field>
              <Field label="存期（年）">
                <input
                  name="deposit_period"
                  type="number"
                  min="1"
                  step="1"
                  defaultValue={asset?.deposit_period ?? ""}
                />
              </Field>
              <Field label="到期日">
                <input
                  name="due_date"
                  type="date"
                  defaultValue={asset?.due_date ?? ""}
                />
              </Field>
            </div>
            <p className="section-note">
              保存后将同步更新金额与归属。普通成员仅可编辑自己名下的资产。
            </p>
            <div className="form-actions">
              <Button type="button" disabled={busy} onClick={onClose}>
                取消
              </Button>
              <Button className="primary" type="submit" disabled={busy}>
                {busy ? "保存中…" : "保存资产"}
              </Button>
            </div>
          </form>
        </FormErrors>
      </div>
    </dialog>
  );
}
