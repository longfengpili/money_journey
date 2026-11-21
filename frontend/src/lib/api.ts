export type Session = {
  user: { id: number; username: string; name: string } | null;
  capabilities: { write_assets: boolean; manage_family: boolean };
  csrf_token: string;
};

export class ApiError extends Error {
  constructor(public code: string, message: string, public fields: Record<string, string[]> = {}) { super(message); }
}

let token = '';
export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json');
  if (options.method && options.method !== 'GET') headers.set('X-CSRFToken', token);
  let response: Response;
  try {
    response = await fetch('/api/v1' + path, { ...options, headers, credentials: 'same-origin' });
  } catch (error) {
    if ((error as Error).name === 'AbortError') throw error;
    throw new ApiError('NETWORK_ERROR', '网络连接失败，提交结果可能尚未确认，请检查后重试');
  }
  let data;
  try { data = await response.json(); } catch { throw new ApiError('SERVER_ERROR', '服务暂时不可用，请稍后重试'); }
  if (!response.ok) {
    if (data.code === 'AUTH_REQUIRED') window.dispatchEvent(new Event('session-expired'));
    if (data.code === 'CSRF_FAILED') void bootstrap();
    throw new ApiError(data.code ?? 'SERVER_ERROR', data.message ?? '操作失败', data.fields ?? {});
  }
  if (data.csrf_token) token = data.csrf_token;
  return data as T;
}

export const bootstrap = () => api<Session>('/auth/context/');
export const jsonBody = (data: unknown) => ({ method: 'POST', body: JSON.stringify(data) });
