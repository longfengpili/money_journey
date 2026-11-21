import { useEffect, useRef, useState } from "react";
import { api, jsonBody } from "../../lib/api";
import { useSession } from "../../app/session";
import { Button, ErrorNotice, Field, FormErrors } from "../../components/ui";

export type MemberDetails = {
  id: number;
  username: string;
  first_name: string;
  is_approved: boolean;
  is_active: boolean;
  is_family_admin: boolean;
  is_superuser: boolean;
  has_login: boolean;
};

export default function MemberEditor({
  member,
  members,
  onClose,
  onSaved,
}: {
  member: MemberDetails;
  members: MemberDetails[];
  onClose: () => void;
  onSaved: (message: string) => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const [busy, setBusy] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [recipientId, setRecipientId] = useState("");
  const [error, setError] = useState<Error>();
  const { session } = useSession();
  const isSelf = session.user?.id === member.id;
  const recipients = members.filter(
    (item) => item.id !== member.id && item.is_active && item.is_approved,
  );
  useEffect(() => {
    const dialog = ref.current!;
    dialog.showModal();
    return () => dialog.close();
  }, []);
  return (
    <dialog
      ref={ref}
      aria-labelledby="member-editor-title"
      onCancel={(event) => {
        event.preventDefault();
        if (!busy) onClose();
      }}
    >
      <div className="card">
        <header className="dialog-head">
          <h2 id="member-editor-title">编辑家庭成员</h2>
          <Button disabled={busy} onClick={onClose}>
            关闭
          </Button>
        </header>
        <p className="section-note">
          账号：{member.username} · {member.has_login ? "可登录" : "不登录"}
        </p>
        <ErrorNotice error={error} />
        <FormErrors error={error}>
          <form
            onSubmit={async (event) => {
              event.preventDefault();
              const values = new FormData(event.currentTarget);
              setBusy(true);
              setError(undefined);
              try {
                await api(`/members/${member.id}/`, {
                  ...jsonBody({
                    first_name: values.get("first_name"),
                    is_active: isSelf
                      ? member.is_active
                      : values.has("is_active"),
                    is_approved: isSelf
                      ? member.is_approved
                      : values.has("is_approved"),
                    is_family_admin: isSelf
                      ? member.is_family_admin
                      : values.has("is_family_admin"),
                  }),
                  method: "PATCH",
                });
                onSaved("成员信息已更新");
              } catch (cause) {
                setError(cause as Error);
              } finally {
                setBusy(false);
              }
            }}
          >
            <fieldset className="member-editor-fields" disabled={busy}>
              <Field label="姓名">
                <input
                  name="first_name"
                  maxLength={150}
                  defaultValue={member.first_name}
                />
              </Field>
              <div className="member-status-grid">
                <label>
                  <input
                    name="is_active"
                    type="checkbox"
                    defaultChecked={member.is_active}
                    disabled={isSelf}
                  />{" "}
                  启用账号
                </label>
                <label>
                  <input
                    name="is_approved"
                    type="checkbox"
                    defaultChecked={member.is_approved}
                    disabled={isSelf}
                  />{" "}
                  已批准
                </label>
                <label>
                  <input
                    name="is_family_admin"
                    type="checkbox"
                    defaultChecked={member.is_family_admin}
                    disabled={isSelf}
                  />{" "}
                  家庭管理员
                </label>
              </div>
            </fieldset>
            <div className="form-actions">
              <Button type="button" disabled={busy} onClick={onClose}>
                取消
              </Button>
              <Button className="primary" type="submit" disabled={busy}>
                {busy ? "保存中…" : "保存成员"}
              </Button>
            </div>
          </form>
        </FormErrors>
        {!isSelf && (
          <div className="member-delete">
            <p>
              删除后该成员将从列表移除并停用，历史快照保留。名下资产会转给所选成员。
            </p>
            {confirmingDelete ? (
              <div>
                <Field label="资产接收成员">
                  <select
                    name="recipient_id"
                    value={recipientId}
                    onChange={(event) => setRecipientId(event.target.value)}
                    required
                    disabled={busy}
                  >
                    <option value="">请选择接收成员</option>
                    {recipients.map((item) => (
                      <option value={item.id} key={item.id}>
                        {item.first_name || item.username}（{item.username}）
                      </option>
                    ))}
                  </select>
                </Field>
                {recipientId && (
                  <p>
                    将资产转给所选成员，并移除{" "}
                    {member.first_name || member.username}。
                  </p>
                )}
                <div className="actions">
                  <Button
                    disabled={busy}
                    onClick={() => setConfirmingDelete(false)}
                  >
                    取消
                  </Button>
                  <Button
                    disabled={busy || !recipientId}
                    onClick={async () => {
                      setBusy(true);
                      setError(undefined);
                      try {
                        const result = await api<{
                          transferred_records: number;
                        }>(`/members/${member.id}/`, {
                          ...jsonBody({ recipient_id: Number(recipientId) }),
                          method: "DELETE",
                        });
                        onSaved(
                          `家庭成员已移除，${result.transferred_records} 条资产已转移`,
                        );
                      } catch (cause) {
                        setError(cause as Error);
                      } finally {
                        setBusy(false);
                      }
                    }}
                  >
                    确认删除
                  </Button>
                </div>
              </div>
            ) : (
              <Button disabled={busy} onClick={() => setConfirmingDelete(true)}>
                删除成员
              </Button>
            )}
          </div>
        )}
      </div>
    </dialog>
  );
}
