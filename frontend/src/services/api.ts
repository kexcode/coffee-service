import { DashboardData, FeedItem, User, Donation, ExpensePayload } from '../types';

let currentInitData = '';
let devUserOverride: { id: number; first_name: string; username?: string; role?: string } | null = null;

export function setApiAuth(initData: string, devUser?: { id: number; first_name: string; username?: string; role?: string }) {
  currentInitData = initData;
  if (devUser) {
    devUserOverride = devUser;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (currentInitData) {
    headers['X-Telegram-Init-Data'] = currentInitData;
  } else if (devUserOverride) {
    headers['X-Dev-Tg-Id'] = String(devUserOverride.id);
    headers['X-Dev-First-Name'] = devUserOverride.first_name;
    if (devUserOverride.username) headers['X-Dev-Username'] = devUserOverride.username;
    if (devUserOverride.role) headers['X-Dev-Role'] = devUserOverride.role;
  }

  const response = await fetch(path, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorMsg = `HTTP Error ${response.status}`;
    try {
      const errJson = await response.json();
      if (errJson.detail) {
        errorMsg = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // ignore
    }
    throw new Error(errorMsg);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

export const api = {
  getDashboard: () => request<DashboardData>('/api/dashboard'),
  getFeed: () => request<FeedItem[]>('/api/feed'),
  getUserMe: () => request<User>('/api/user/me'),
  updatePledge: (pledge_amount: number, pledge_active: boolean) =>
    request<User>('/api/pledge', {
      method: 'POST',
      body: JSON.stringify({ pledge_amount, pledge_active }),
    }),
  submitCashDonation: (amount: number) =>
    request<Donation>('/api/donations/cash', {
      method: 'POST',
      body: JSON.stringify({ amount }),
    }),

  // Admin APIs
  adminCreateExpense: (data: ExpensePayload) =>
    request<any>('/api/admin/expenses', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  adminDeleteExpense: (expenseId: number) =>
    request<void>(`/api/admin/expenses/${expenseId}`, {
      method: 'DELETE',
    }),
  adminGetPendingDonations: () =>
    request<Donation[]>('/api/admin/donations/pending'),
  adminConfirmDonation: (donationId: number) =>
    request<Donation>(`/api/admin/donations/${donationId}/confirm`, {
      method: 'POST',
    }),
  adminRejectDonation: (donationId: number) =>
    request<Donation>(`/api/admin/donations/${donationId}/reject`, {
      method: 'POST',
    }),
  adminGetSettings: () =>
    request<Record<string, string>>('/api/admin/settings'),
  adminUpdateSetting: (key: string, value: string) =>
    request<{ key: string; value: string }>(`/api/admin/settings/${key}`, {
      method: 'POST',
      body: JSON.stringify({ value }),
    }),
  adminTriggerReminders: () =>
    request<{ message: string }>('/api/admin/trigger-reminders', {
      method: 'POST',
    }),
};
