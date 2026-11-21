import { createContext, useContext } from "react";
import type { Session } from "../lib/api";

export const SessionContext = createContext<{
  session: Session;
  refresh: () => Promise<void>;
} | null>(null);
export function useSession() {
  const value = useContext(SessionContext);
  if (!value) throw new Error("身份上下文未就绪");
  return value;
}
