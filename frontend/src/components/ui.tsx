import {
  cloneElement,
  createContext,
  isValidElement,
  useContext,
  useId,
  type ReactNode,
} from "react";
import { ApiError } from "../lib/api";
import { Button as BoardButton, type ButtonProps } from "./base/buttons/button";

export function Button(props: ButtonProps) {
  return (
    <BoardButton
      variant={props.className?.includes("primary") ? "primary" : "secondary"}
      {...props}
    />
  );
}

const FieldErrors = createContext<Record<string, string[]>>({});
export function FormErrors({
  error,
  children,
}: {
  error?: Error;
  children: ReactNode;
}) {
  return (
    <FieldErrors.Provider value={error instanceof ApiError ? error.fields : {}}>
      {children}
    </FieldErrors.Provider>
  );
}

const labels: Record<string, string> = {
  username: "用户名",
  password: "密码",
  password1: "密码",
  password2: "确认密码",
  first_name: "姓名",
  email: "邮箱",
  owner_id: "所有者",
  amount: "金额",
  bank: "银行",
  category: "类别",
  interest_rate: "利率",
  deposit_period: "存期",
  due_date: "到期日",
  __all__: "提示",
  basic: "基本参数",
  age_ranges: "年龄段",
  end_age: "结束年龄",
  start_age: "起始年龄",
  monthly_income: "月收入",
  monthly_expense: "月支出",
};

export function ErrorNotice({ error }: { error?: Error | null }) {
  if (!error) return null;
  return (
    <div className="notice error" role="alert">
      <strong>{error.message}</strong>
      {error instanceof ApiError &&
        Object.entries(error.fields).map(([key, values]) => (
          <div key={key}>
            {labels[key] || labels[key.split(".").at(-1)!] || "输入参数"}：
            {Array.isArray(values) ? values.join("；") : String(values)}
          </div>
        ))}
    </div>
  );
}
export function Field({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  const errors = useContext(FieldErrors);
  const id = useId();
  const child = isValidElement<{
    name?: string;
    id?: string;
    "aria-invalid"?: boolean;
    "aria-describedby"?: string;
  }>(children)
    ? children
    : null;
  const issues = child?.props.name ? errors[child.props.name] || [] : [];
  const control = child
    ? cloneElement(child, {
        id: child.props.id || id,
        "aria-invalid": issues.length ? true : undefined,
        "aria-describedby": issues.length ? id + "-error" : undefined,
      })
    : children;
  return (
    <label className="field">
      <span>{label}</span>
      {control}
      {issues.length > 0 && (
        <span id={id + "-error"} className="field-error">
          {issues.join("；")}
        </span>
      )}
    </label>
  );
}
export function PageTitle({
  title,
  detail,
  actions,
}: {
  title: string;
  detail: string;
  actions?: ReactNode;
}) {
  return (
    <header className="page-title">
      <div>
        <h1>{title}</h1>
        <p>{detail}</p>
      </div>
      <div className="actions">{actions}</div>
    </header>
  );
}
export function Loading() {
  return (
    <div className="card loading" role="status">
      正在读取数据…
    </div>
  );
}
