import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api, jsonBody } from '../../lib/api';
import { useSession } from '../../app/session';
import { Button, ErrorNotice, Field } from '../../components/ui';

export default function Login() {
  const [error, setError] = useState<Error>();
  const [busy, setBusy] = useState(false);
  const { refresh } = useSession();
  const navigate = useNavigate();
  return <section className="auth-card card"><div className="eyebrow">WELCOME HOME</div><h1>登录家庭资金空间</h1><p>一处查看家庭资产，清楚规划每一步。</p><ErrorNotice error={error}/><form onSubmit={async event => {
    event.preventDefault(); setBusy(true); setError(undefined);
    const data = new FormData(event.currentTarget);
    try { await api('/auth/login/', jsonBody(Object.fromEntries(data))); await refresh(); navigate('/'); }
    catch (e) { setError(e as Error); } finally { setBusy(false); }
  }}><Field label="用户名"><input name="username" required autoComplete="username"/></Field><Field label="密码"><input name="password" type="password" required autoComplete="current-password"/></Field><Button className="primary" disabled={busy}>{busy ? '登录中…' : '登录'}</Button></form><p>还没有账号？<Link to="/register">注册并等待管理员批准</Link></p><Link to="/">先浏览演示</Link></section>;
}
