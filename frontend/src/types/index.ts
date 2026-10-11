export interface User {
  id: number;
  tg_id: number;
  username?: string | null;
  first_name: string;
  role: 'admin' | 'user';
  is_verified: boolean;
  pledge_amount: number;
  pledge_active: boolean;
  created_at: string;
}

export interface AdminUser extends User {
  total_donated: number;
}

export interface DashboardData {
  is_verified: boolean;
  total_balance: number;
  monthly_target: number;
  monthly_collected: number;
  monthly_expenses: number;
  total_donations: number;
  total_expenses: number;
  active_pledgers_count: number;
  total_pledged_monthly: number;
  category_breakdown: Record<string, number>;
  paypal_me_url: string;
}

export interface FeedItem {
  id: number;
  type: 'donation' | 'expense';
  amount: number;
  description: string;
  category?: string | null;
  payment_method?: string | null;
  status?: string | null;
  user_id?: number | null;
  actor_name: string;
  actor_username?: string | null;
  receipt_url?: string | null;
  created_at: string;
}

export interface Donation {
  id: number;
  user_id: number;
  amount: number;
  payment_method: string;
  status: string;
  created_at: string;
  user_first_name?: string | null;
  user_username?: string | null;
}

export interface ExpensePayload {
  category: 'beans' | 'sweets' | 'filters' | 'cleaning' | 'maintenance_repair' | 'depreciation_reserve';
  amount: number;
  description: string;
  receipt_url?: string;
}

export interface CSVImportItem {
  date: string;
  category: string;
  amount: number;
  contributor?: string | null;
  type: 'expense' | 'donation';
  resolved_contributor: string;
}

export interface CSVImportSummary {
  total_rows: number;
  expenses_imported: number;
  donations_imported: number;
  anonymous_donations: number;
  errors: string[];
  preview?: CSVImportItem[] | null;
}

