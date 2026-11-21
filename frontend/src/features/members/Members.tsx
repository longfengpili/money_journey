import { useState } from 'react';
import { api, jsonBody } from '../../lib/api';
import { useResource } from '../../lib/resource';
import { Button, ErrorNotice, Field, Loading, PageTitle } from '../../components/ui';

type Member = { id: number; username: string; first_name: string; is_approved: boolean; is_active: boolean; is_family_admin: boolean; has_login: boolean };
export default function Members() {
  const [version, setVersion] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error>();
  const [notice, setNotice] = useState('');
  const state = useResource<{ results: Member[] }>('/members/', version);
  return <><PageTitle title="家庭成员" detail="批准注册账号，或为不登录的家人建立资产归属。"/><ErrorNotice error={error || state.error}/>{notice && <div className="notice success" role="status">{notice}</div>}{state.loading ? <Loading/> : state.data && <div className="stack"><section className="card"><h2>成员账号</h2><div className="table-wrap"><table><thead><tr><th>姓名与账号</th><th>角色</th><th>账号状态</th><th>操作</th></tr></thead><tbody>{state.data.results.map(member => <tr key={member.id}><td className="break"><strong>{member.first_name || member.username}</strong><div className="label">{member.username}</div></td><td>{member.is_family_admin ? '家庭管理员' : '家庭成员'}</td><td>{!member.is_active ? '已停用' : !member.is_approved ? '待批准' : member.has_login ? '可登录' : '不登录的成员'}</td><td>{!member.is_approved ? <Button disabled={busy} onClick={async () => {
    setBusy(true); setError(undefined); setNotice('');
    try { await api(`/approvals/${member.id}/`, jsonBody({})); setNotice('账号已批准'); setVersion(version + 1); }
    catch (e) { setError(e as Error); } finally { setBusy(false); }
  }}>批准加入</Button> : <span className="muted">已批准</span>}</td></tr>)}</tbody></table></div></section><section className="card"><h2>创建不登录的家庭成员</h2><p>用于为家人记录资产，不设置密码，也不会赋予管理员权限。</p><form onSubmit={async event => {
    event.preventDefault(); const form = event.currentTarget; setBusy(true); setError(undefined); setNotice('');
    try { await api('/members/', jsonBody(Object.fromEntries(new FormData(form)))); form.reset(); setNotice('家庭成员已创建，可以为其录入资产'); setVersion(version + 1); }
    catch (e) { setError(e as Error); } finally { setBusy(false); }
  }}><div className="form-grid"><Field label="用户名"><input name="username" required maxLength={150}/></Field><Field label="姓名"><input name="first_name" maxLength={150}/></Field></div><div className="form-actions"><Button className="primary" disabled={busy}>{busy ? '处理中…' : '创建家庭成员'}</Button></div></form></section></div>}</>;
}
