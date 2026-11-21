import { useEffect, useState } from 'react';
import { api } from './api';

export function useResource<T>(url: string, version = 0) {
  const [state, setState] = useState<{ data?: T; error?: Error; loading: boolean }>({ loading: true });
  useEffect(() => {
    const controller = new AbortController();
    setState({ loading: true });
    api<T>(url, { signal: controller.signal }).then(
      data => { if (!controller.signal.aborted) setState({ data, loading: false }); },
      error => { if (!controller.signal.aborted) setState({ error, loading: false }); },
    );
    return () => controller.abort();
  }, [url, version]);
  return state;
}
