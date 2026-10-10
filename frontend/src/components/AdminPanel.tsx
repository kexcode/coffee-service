import React, { useState, useEffect } from 'react';
import { Shield, PlusCircle, Check, X, Settings as SettingsIcon, Bell } from 'lucide-react';
import { Donation, ExpensePayload } from '../types';
import { api } from '../services/api';

interface AdminPanelProps {
  onDataChanged: () => void;
  triggerHaptic?: (type: 'light' | 'success' | 'error') => void;
}

const EXPENSE_CATEGORIES: { key: ExpensePayload['category']; label: string }[] = [
  { key: 'beans', label: '☕ Coffee Beans' },
  { key: 'filters', label: '📄 Paper & Filters' },
  { key: 'cleaning', label: '🧼 Cleaning & Descaling' },
  { key: 'maintenance_repair', label: '🔧 Maintenance & Parts' },
  { key: 'depreciation_reserve', label: '🏦 Equipment Reserve' },
];

export const AdminPanel: React.FC<AdminPanelProps> = ({ onDataChanged, triggerHaptic }) => {
  const [pendingDonations, setPendingDonations] = useState<Donation[]>([]);

  // Expense form state
  const [category, setCategory] = useState<ExpensePayload['category']>('beans');
  const [amount, setAmount] = useState('');
  const [description, setDescription] = useState('');
  const [receiptUrl, setReceiptUrl] = useState('');
  const [isSubmittingExpense, setIsSubmittingExpense] = useState(false);
  const [expenseSuccess, setExpenseSuccess] = useState(false);

  // Settings state
  const [monthlyTargetInput, setMonthlyTargetInput] = useState('');
  const [paypalInput, setPaypalInput] = useState('');
  const [isSavingSettings, setIsSavingSettings] = useState(false);
  const [settingsSuccess, setSettingsSuccess] = useState(false);

  // Reminders trigger state
  const [isTriggeringReminders, setIsTriggeringReminders] = useState(false);
  const [reminderMsg, setReminderMsg] = useState<string | null>(null);

  const loadAdminData = async () => {
    try {
      const [pending, settingsRes] = await Promise.all([
        api.adminGetPendingDonations(),
        api.adminGetSettings(),
      ]);
      setPendingDonations(pending);
      setMonthlyTargetInput(settingsRes.monthly_target || '150.00');
      setPaypalInput(settingsRes.paypal_me_url || '');
    } catch (e) {
      console.error('Failed to load admin data:', e);
    }
  };

  useEffect(() => {
    loadAdminData();
  }, []);

  const handleConfirmDonation = async (id: number) => {
    try {
      await api.adminConfirmDonation(id);
      triggerHaptic?.('success');
      setPendingDonations((prev) => prev.filter((d) => d.id !== id));
      onDataChanged();
    } catch (e) {
      triggerHaptic?.('error');
      console.error('Failed to confirm donation:', e);
    }
  };

  const handleRejectDonation = async (id: number) => {
    try {
      await api.adminRejectDonation(id);
      triggerHaptic?.('error');
      setPendingDonations((prev) => prev.filter((d) => d.id !== id));
      onDataChanged();
    } catch (e) {
      console.error('Failed to reject donation:', e);
    }
  };

  const handleAddExpense = async (e: React.FormEvent) => {
    e.preventDefault();
    const parsedAmount = parseFloat(amount);
    if (isNaN(parsedAmount) || parsedAmount <= 0 || !description.trim()) {
      return;
    }

    setIsSubmittingExpense(true);
    try {
      await api.adminCreateExpense({
        category,
        amount: parsedAmount,
        description: description.trim(),
        receipt_url: receiptUrl.trim() || undefined,
      });
      triggerHaptic?.('success');
      setExpenseSuccess(true);
      setAmount('');
      setDescription('');
      setReceiptUrl('');
      onDataChanged();
      setTimeout(() => setExpenseSuccess(false), 3000);
    } catch (e) {
      triggerHaptic?.('error');
      console.error('Failed to create expense:', e);
    } finally {
      setIsSubmittingExpense(false);
    }
  };

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSavingSettings(true);
    try {
      await Promise.all([
        api.adminUpdateSetting('monthly_target', monthlyTargetInput.trim()),
        api.adminUpdateSetting('paypal_me_url', paypalInput.trim()),
      ]);
      triggerHaptic?.('success');
      setSettingsSuccess(true);
      onDataChanged();
      setTimeout(() => setSettingsSuccess(false), 2500);
    } catch (e) {
      triggerHaptic?.('error');
      console.error('Failed to update settings:', e);
    } finally {
      setIsSavingSettings(false);
    }
  };

  const handleTriggerReminders = async () => {
    setIsTriggeringReminders(true);
    setReminderMsg(null);
    try {
      const res = await api.adminTriggerReminders();
      triggerHaptic?.('success');
      setReminderMsg(res.message);
      setTimeout(() => setReminderMsg(null), 4000);
    } catch (e: any) {
      triggerHaptic?.('error');
      setReminderMsg(e.message || 'Error triggering reminders');
    } finally {
      setIsTriggeringReminders(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Pending Cash Approvals */}
      <div className="bg-white rounded-3xl p-5 shadow-warm border border-amber-200">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 rounded-xl bg-amber-100 text-amber-800 flex items-center justify-center">
              <Shield className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-coffee-espresso">Cash Jar Approvals</h3>
              <p className="text-[11px] text-stone-500">
                {pendingDonations.length} pending cash payment{pendingDonations.length === 1 ? '' : 's'}
              </p>
            </div>
          </div>
        </div>

        {pendingDonations.length === 0 ? (
          <div className="p-3 bg-stone-50 rounded-2xl text-center text-xs text-stone-400">
            No pending cash donations to verify. All good! 👍
          </div>
        ) : (
          <div className="space-y-2">
            {pendingDonations.map((item) => (
              <div
                key={item.id}
                className="p-3 bg-amber-50/60 rounded-2xl border border-amber-200/60 flex items-center justify-between"
              >
                <div>
                  <div className="text-xs font-bold text-coffee-espresso">
                    {item.user_first_name || 'Member'}
                  </div>
                  <div className="text-[11px] font-semibold text-emerald-800">
                    Dropped €{item.amount.toFixed(2)} in cash
                  </div>
                  <div className="text-[10px] text-stone-400">
                    {new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </div>
                </div>

                <div className="flex items-center space-x-1.5">
                  <button
                    onClick={() => handleConfirmDonation(item.id)}
                    className="p-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm transition-all"
                    title="Confirm Receipt"
                  >
                    <Check className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => handleRejectDonation(item.id)}
                    className="p-2 rounded-xl bg-rose-100 hover:bg-rose-200 text-rose-700 transition-all"
                    title="Reject"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Record Station Expense */}
      <div className="bg-white rounded-3xl p-5 shadow-warm border border-coffee-border/70">
        <div className="flex items-center space-x-2 mb-3">
          <div className="w-8 h-8 rounded-xl bg-coffee-cream text-coffee-espresso flex items-center justify-center">
            <PlusCircle className="w-4 h-4 text-coffee-caramel" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-coffee-espresso">Record Station Expense</h3>
            <p className="text-[11px] text-stone-500">Log beans, milk, filters, or repairs</p>
          </div>
        </div>

        {expenseSuccess && (
          <div className="mb-3 p-2.5 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs rounded-xl flex items-center gap-1.5">
            <Check className="w-4 h-4 text-emerald-600" />
            Expense recorded successfully!
          </div>
        )}

        <form onSubmit={handleAddExpense} className="space-y-3">
          <div>
            <label className="block text-[11px] font-semibold text-coffee-latte uppercase tracking-wider mb-1">
              Category
            </label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value as ExpensePayload['category'])}
              className="w-full text-xs font-semibold p-2.5 rounded-xl border border-stone-200 bg-stone-50 focus:bg-white focus:outline-none focus:ring-1 focus:ring-coffee-latte text-coffee-espresso"
            >
              {EXPENSE_CATEGORIES.map((cat) => (
                <option key={cat.key} value={cat.key}>
                  {cat.label}
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-[11px] font-semibold text-coffee-latte uppercase tracking-wider mb-1">
                Amount (€)
              </label>
              <input
                type="number"
                step="0.01"
                min="0.1"
                placeholder="e.g. 18.50"
                required
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                className="w-full text-xs font-bold p-2.5 rounded-xl border border-stone-200 bg-stone-50 focus:bg-white focus:outline-none focus:ring-1 focus:ring-coffee-latte text-coffee-espresso"
              />
            </div>
            <div>
              <label className="block text-[11px] font-semibold text-coffee-latte uppercase tracking-wider mb-1">
                Receipt Link (Optional)
              </label>
              <input
                type="url"
                placeholder="https://..."
                value={receiptUrl}
                onChange={(e) => setReceiptUrl(e.target.value)}
                className="w-full text-xs p-2.5 rounded-xl border border-stone-200 bg-stone-50 focus:bg-white focus:outline-none focus:ring-1 focus:ring-coffee-latte text-coffee-espresso"
              />
            </div>
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-coffee-latte uppercase tracking-wider mb-1">
              Description
            </label>
            <input
              type="text"
              placeholder="e.g., 2kg Honduras Arabica beans from local roastery"
              required
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full text-xs p-2.5 rounded-xl border border-stone-200 bg-stone-50 focus:bg-white focus:outline-none focus:ring-1 focus:ring-coffee-latte text-coffee-espresso"
            />
          </div>

          <button
            type="submit"
            disabled={isSubmittingExpense}
            className="w-full py-2.5 bg-coffee-espresso hover:bg-coffee-roast text-white rounded-xl font-bold text-xs shadow-sm transition-all disabled:opacity-50"
          >
            {isSubmittingExpense ? 'Logging...' : 'Save & Publish Expense'}
          </button>
        </form>
      </div>

      {/* Community Settings */}
      <div className="bg-white rounded-3xl p-5 shadow-warm border border-coffee-border/70">
        <div className="flex items-center space-x-2 mb-3">
          <div className="w-8 h-8 rounded-xl bg-stone-100 text-stone-700 flex items-center justify-center">
            <SettingsIcon className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-coffee-espresso">Treasury Settings</h3>
            <p className="text-[11px] text-stone-500">Configure targets & payment links</p>
          </div>
        </div>

        {settingsSuccess && (
          <div className="mb-3 p-2 bg-emerald-50 text-emerald-800 text-xs rounded-xl flex items-center gap-1.5">
            <Check className="w-3.5 h-3.5 text-emerald-600" />
            Settings saved!
          </div>
        )}

        <form onSubmit={handleSaveSettings} className="space-y-3">
          <div>
            <label className="block text-[11px] font-semibold text-coffee-latte uppercase tracking-wider mb-1">
              Monthly Fund Target (€)
            </label>
            <input
              type="number"
              step="5"
              value={monthlyTargetInput}
              onChange={(e) => setMonthlyTargetInput(e.target.value)}
              className="w-full text-xs font-bold p-2.5 rounded-xl border border-stone-200 bg-stone-50 text-coffee-espresso"
            />
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-coffee-latte uppercase tracking-wider mb-1">
              PayPal.me Link
            </label>
            <input
              type="url"
              value={paypalInput}
              onChange={(e) => setPaypalInput(e.target.value)}
              className="w-full text-xs p-2.5 rounded-xl border border-stone-200 bg-stone-50 text-coffee-espresso"
            />
          </div>

          <button
            type="submit"
            disabled={isSavingSettings}
            className="w-full py-2 bg-stone-800 hover:bg-stone-900 text-white rounded-xl font-bold text-xs transition-all disabled:opacity-50"
          >
            {isSavingSettings ? 'Saving...' : 'Update Settings'}
          </button>
        </form>

        {/* Trigger Reminders Button */}
        <div className="mt-4 pt-3 border-t border-stone-100">
          <button
            onClick={handleTriggerReminders}
            disabled={isTriggeringReminders}
            className="w-full py-2 bg-amber-50 hover:bg-amber-100 border border-amber-200 text-amber-900 rounded-xl font-semibold text-xs flex items-center justify-center gap-1.5 transition-all"
          >
            <Bell className="w-3.5 h-3.5" />
            <span>{isTriggeringReminders ? 'Broadcasting...' : 'Broadcast Monthly Reminder Now (Test)'}</span>
          </button>
          {reminderMsg && (
            <p className="text-[10px] text-center text-stone-500 mt-1.5">{reminderMsg}</p>
          )}
        </div>
      </div>
    </div>
  );
};
