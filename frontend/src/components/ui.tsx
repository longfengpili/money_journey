import type { ReactNode } from 'react';
import { ApiError } from '../lib/api';
import { Button as BoardButton, type ButtonProps } from './base/buttons/button';

export function Button(props: ButtonProps) {
  return <BoardButton variant={props.className?.includes('primary') ? 'primary' : 'secondary'} {...props}/>;
}

export function ErrorNotice({ error }: { error?: Error | null }) {
  if (!error) return null;
  return <div className="notice error" role="alert"><strong>{error.message}</strong>{error instanceof ApiError && Object.entries(error.fields).map(([key, values]) => <div key={key}>{key}: {Array.isArray(values) ? values.join('；') : String(values)}</div>)}</div>;
}
export function Field({ label, children }: { label: string; children: ReactNode }) {
  return <label className="field"><span>{label}</span>{children}</label>;
}
export function PageTitle({ title, detail, actions }: { title: string; detail: string; actions?: ReactNode }) {
  return <header className="page-title"><div><h1>{title}</h1><p>{detail}</p></div><div className="actions">{actions}</div></header>;
}
export function Loading() { return <div className="card loading" role="status">正在读取数据…</div>; }
