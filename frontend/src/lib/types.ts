export type Member = { id: number; username: string; first_name: string };
export type Choices = [string, string][];
export type SummaryRow = { owner?: string; first_name?: string; bank?: string; bank_display?: string; category?: string; category_display?: string; savings_status?: string; savings_status_display?: string; total_amount: string; record_count: number };
export type Summary = {
  demo: boolean; total_amount: string; total_records: number; owner_count: number;
  owner_summary: SummaryRow[]; bank_summary: SummaryRow[]; category_summary: SummaryRow[];
  status_summary: SummaryRow[]; owner_choices: Member[]; bank_choices: Choices;
  category_choices: Choices; status_choices: Choices;
};
export type Asset = {
  id: number; user_id: number | null; owner: string; owner_display: string;
  bank: string; bank_display: string; category: string; category_display: string;
  amount: string; savings_status: string; status_display: string;
  interest_rate: string | null; deposit_period: number | null;
  due_date: string | null; start_date: string | null; can_edit: boolean;
};
export type FundOptions = { owners: Member[]; bank_choices: Choices; category_choices: Choices; status_choices: Choices };
