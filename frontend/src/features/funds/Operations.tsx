import { useState } from 'react';
import { useSession } from '../../app/session';
import { api, jsonBody } from '../../lib/api';
import { Button, ErrorNotice, Field, PageTitle } from '../../components/ui';

type ImportResult = { success_count: number; error_count: number; errors: string[] };
export default function Operations() {
  const { session } = useSession();
  const [importing, setImporting] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<Error>();
  const [result, setResult] = useState<ImportResult>();
  const [snapshot, setSnapshot] = useState('');
  return <><PageTitle title="导入与快照" detail="批量录入资产，并保存当天家庭资金状态。"/><ErrorNotice error={error}/><div className="grid-two"><section className="card"><h2>CSV 批量导入</h2><p>使用模板整理资产，上传后查看成功数量与错误行。</p><a className="button" href="/api/v1/funds/import-template/" download>下载 CSV 模板</a><form style={{ marginTop: 24 }} onSubmit={async event => {
    event.preventDefault(); setError(undefined); setResult(undefined); setImporting(true);
    try { setResult(await api<ImportResult>('/funds/import/', { method: 'POST', body: new FormData(event.currentTarget) })); }
    catch (e) { setError(e as Error); } finally { setImporting(false); }
  }}><Field label="CSV 文件"><input name="csv_file" type="file" accept=".csv" required disabled={importing}/></Field><p className="section-note">UTF-8 编码，最大 10MB、10000 行。合法行统一保存，校验错误行不写入。</p><Button className="primary" disabled={importing} type="submit">{importing ? '正在导入…' : '上传并导入'}</Button></form>{result && <div className="notice" role="status" style={{ marginTop: 24 }}><strong>成功导入 {result.success_count} 条，校验失败 {result.error_count} 条</strong>{result.errors.map((error, index) => <p className="break" key={index}>{error}</p>)}{result.error_count > result.errors.length && <p>仅展示前 {result.errors.length} 条错误，请修正文件后检查其余行。</p>}</div>}</section><section className="card"><h2>当天家庭资金快照</h2><p>汇总全家存续中的资产。同一天重复刷新会更新当天快照，历史日期保持原样。</p>{session.capabilities.manage_family ? <Button className="primary" disabled={refreshing} onClick={async () => {
    setRefreshing(true); setError(undefined); setSnapshot('');
    try { const result = await api<{ snapshot_date: string; created_count: number; updated_count: number }>('/snapshots/refresh/', jsonBody({})); setSnapshot(`${result.snapshot_date} 快照已刷新：新增 ${result.created_count} 条，更新 ${result.updated_count} 条`); }
    catch (e) { setError(e as Error); } finally { setRefreshing(false); }
  }}>{refreshing ? '正在刷新…' : '刷新当天快照'}</Button> : <div className="notice">由家庭管理员刷新快照，所有成员均可在总览查看趋势。</div>}{snapshot && <div className="notice success" role="status" style={{ marginTop: 24 }}>{snapshot}</div>}</section></div></>;
}
