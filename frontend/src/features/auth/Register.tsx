import { useState } from "react";
import { Link } from "react-router-dom";
import { api, jsonBody } from "../../lib/api";
import { Button, ErrorNotice, FormErrors, Field } from "../../components/ui";

export default function Register() {
  const [error, setError] = useState<Error>();
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  return (
    <section className="auth-card card">
      <div className="eyebrow">JOIN YOUR FAMILY</div>
      <h1>注册家庭账号</h1>
      <p>每个账号代表一位家庭成员，注册后需要管理员批准。</p>
      {done ? (
        <>
          <div className="notice success" role="status">
            注册成功，请等待家庭管理员批准后再登录。
          </div>
          <Link to="/login" className="button primary">
            前往登录
          </Link>
        </>
      ) : (
        <>
          <ErrorNotice error={error} />
          <FormErrors error={error}>
            <form
              onSubmit={async (event) => {
                event.preventDefault();
                setBusy(true);
                setError(undefined);
                try {
                  await api(
                    "/auth/register/",
                    jsonBody(
                      Object.fromEntries(new FormData(event.currentTarget)),
                    ),
                  );
                  setDone(true);
                } catch (e) {
                  setError(e as Error);
                } finally {
                  setBusy(false);
                }
              }}
            >
              <Field label="用户名">
                <input
                  name="username"
                  required
                  maxLength={150}
                  autoComplete="username"
                />
              </Field>
              <Field label="姓名">
                <input name="first_name" maxLength={150} autoComplete="name" />
              </Field>
              <Field label="邮箱（可选）">
                <input name="email" type="email" autoComplete="email" />
              </Field>
              <Field label="密码">
                <input
                  name="password1"
                  type="password"
                  required
                  minLength={8}
                  autoComplete="new-password"
                />
              </Field>
              <Field label="确认密码">
                <input
                  name="password2"
                  type="password"
                  required
                  minLength={8}
                  autoComplete="new-password"
                />
              </Field>
              <p className="section-note">
                至少 8 位，避免与个人信息相似、常见密码和纯数字。
              </p>
              <Button className="primary" type="submit" disabled={busy}>
                {busy ? "注册中…" : "提交注册"}
              </Button>
            </form>
          </FormErrors>
          <Link to="/login">已有账号，返回登录</Link>
        </>
      )}
    </section>
  );
}
