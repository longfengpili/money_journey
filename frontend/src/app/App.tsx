import { useCallback, useEffect, useState } from 'react';
import { BrowserRouter, Link, NavLink, Navigate, Route, Routes, useNavigate } from 'react-router-dom';
import { api, bootstrap, jsonBody, type Session } from '../lib/api';
import { SessionContext, useSession } from './session';
import { Button, ErrorNotice, Loading, PageTitle } from '../components/ui';
import Login from '../features/auth/Login';
import Dashboard from '../features/dashboard/Dashboard';
import Funds from '../features/funds/Funds';
import Operations from '../features/funds/Operations';

function MemberPage({ children }: { children: React.ReactNode }) {
  const { session } = useSession();
  if (!session.user) return <Navigate to="/login" replace/>;
  if (!session.capabilities.write_assets) return <div className="notice error" role="alert">账号尚未批准或已停用，请联系家庭管理员。</div>;
  return children;
}

function Workspace() {
  const { session, refresh } = useSession();
  const [menu, setMenu] = useState(false);
  const [error, setError] = useState<Error>();
  const navigate = useNavigate();
  useEffect(() => {
    const expired = () => { void refresh(); navigate('/login'); };
    window.addEventListener('session-expired', expired);
    return () => window.removeEventListener('session-expired', expired);
  }, [refresh, navigate]);
  return <div className="app-layout"><aside className={menu ? 'sidebar open' : 'sidebar'}><Link className="brand" to="/"><span className="brand-mark">MJ</span><span>Money Journey<small>家庭资金空间</small></span></Link><nav onClick={() => setMenu(false)} aria-label="主要导航"><NavLink end to="/">资金总览</NavLink><NavLink to="/funds">资产记录</NavLink><NavLink to="/operations">导入与快照</NavLink><NavLink to="/calculator">储蓄规划</NavLink>{session.capabilities.manage_family && <NavLink to="/members">家庭成员</NavLink>}</nav><div className="sidebar-bottom"><span className="label">一个家庭 · 共同规划</span><a href="/analytics/dashboard/">返回原版页面 ↗</a></div></aside><div className="workspace"><header className="topbar"><Button className="menu-toggle" aria-label="切换导航" aria-expanded={menu} onClick={() => setMenu(!menu)}>☰</Button><span className="label">记录今天，规划未来</span><div className="actions">{session.user ? <><span>{session.user.name}</span><span className="badge">{session.capabilities.manage_family ? '家庭管理员' : '家庭成员'}</span><Button onClick={async () => {
    try { await api('/auth/logout/', jsonBody({})); await refresh(); navigate('/login'); } catch (e) { setError(e as Error); }
  }}>退出</Button></> : <><span className="badge">演示模式</span><Link to="/login" className="button primary">登录</Link></>}</div></header><main key={session.user?.id ?? 'guest'}><ErrorNotice error={error}/><Routes><Route path="/" element={<Dashboard/>}/><Route path="/operations" element={<MemberPage><Operations/></MemberPage>}/><Route path="/funds" element={<MemberPage><Funds/></MemberPage>}/><Route path="/login" element={<Login/>}/><Route path="*" element={<><PageTitle title="家庭资金总览" detail="统一管理家庭资产，让每一笔资金清晰可见。"/><div className="card">工作区已就绪，业务页面正在按阶段迁移。</div></>}/></Routes></main></div></div>;
}

export default function App() {
  const [session, setSession] = useState<Session>();
  const [error, setError] = useState<Error>();
  const refresh = useCallback(async () => { setSession(await bootstrap()); }, []);
  useEffect(() => { refresh().catch(setError); }, [refresh]);
  if (error) return <div className="auth-card card"><ErrorNotice error={error}/><Button onClick={() => window.location.reload()}>重新连接</Button></div>;
  if (!session) return <Loading/>;
  return <SessionContext.Provider value={{ session, refresh }}><BrowserRouter basename="/app"><Workspace/></BrowserRouter></SessionContext.Provider>;
}
