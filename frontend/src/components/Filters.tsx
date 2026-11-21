import type { Choices, Member } from '../lib/types';
import { Button, Field } from './ui';

export default function Filters({ params, onChange, owners, banks, categories, statuses }: {
  params: URLSearchParams; onChange: (params: URLSearchParams) => void;
  owners: Member[]; banks: Choices; categories: Choices; statuses: Choices;
}) {
  const change = (key: string, value: string) => { const next = new URLSearchParams(params); next.set(key, value); next.delete('page'); onChange(next); };
  return <div className="card filters"><Field label="所有者"><select aria-label="筛选所有者" value={params.get('owner_id') ?? ''} onChange={e => change('owner_id', e.target.value)}><option value="">全家成员</option>{owners.map(member => <option key={member.id} value={member.id}>{member.first_name || member.username}</option>)}</select></Field>{([
    ['bank', '银行', banks], ['category', '类别', categories], ['savings_status', '状态', statuses],
  ] as [string, string, Choices][]).map(([key, label, choices]) => <Field key={key} label={label}><select aria-label={'筛选' + label} value={params.get(key) ?? (key === 'savings_status' ? 'ACTIVE' : '')} onChange={e => change(key, e.target.value)}><option value="">全部{label}</option>{choices.map(([code, text]) => <option key={code} value={code}>{text}</option>)}</select></Field>)}<Button onClick={() => onChange(new URLSearchParams())}>重置筛选</Button></div>;
}
