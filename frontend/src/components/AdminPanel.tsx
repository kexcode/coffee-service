import React, { useState, useEffect } from 'react';
import {
  Shield,
  PlusCircle,
  Check,
  X,
  Settings as SettingsIcon,
  Bell,
  Users,
  UserCheck,
  UserX,
  Crown,
  Search,
  AlertCircle,
  Clock,
} from 'lucide-react';
import { Donation, ExpensePayload, AdminUser } from '../types';
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
  const [adminSection, setAdminSection] = useState<'operations' | 'members' | 'settings'>('operations');
  const [pendingDonations, setPendingDonations] = useState<Donation[]>([]);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [userSearch, setUserSearch] = useState('');
  const [userActionError, setUserActionError] = useState<string | null>(null);

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
      const [pending, settingsRes, usersRes] = await Promise.all([
        api.adminGetPendingDonations(),
        api.adminGetSettings(),
        api.adminGetUsers().catch(() => []),
      ]);
      setPendingDonations(pending);
      setMonthlyTargetInput(settingsRes.monthly_target || '150.00');
      setPaypalInput(settingsRes.paypal_me_url || '');
      setUsers(usersRes);
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
      // Reload users to update lifetime donated amounts
      api.adminGetUsers().then(setUsers).catch(() => {});
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

  const handleToggleVerification = async (targetUser: AdminUser) => {
    setUserActionError(null);
    const newStatus = !targetUser.is_verified;
    try {
      await api.adminUpdateUserVerification(targetUser.id, newStatus);
      triggerHaptic?.('success');
      setUsers((prev) =>
        prev.map((u) => (u.id === targetUser.id ? { ...u, is_verified: newStatus } : u))
      );
      onDataChanged();
    } catch (err: any) {
      triggerHaptic?.('error');
      setUserActionError(err.message || 'Failed to update verification status');
    }
  };

  const handleToggleRole = async (targetUser: AdminUser) => {
    setUserActionError(null);
    const newRole = targetUser.role === 'admin' ? 'user' : 'admin';
    const confirmMsg =
      newRole === 'admin'
        ? `Are you sure you want to promote ${targetUser.first_name} to Admin?`
        : `Are you sure you want to demote ${targetUser.first_name} to regular Member?`;

    if (!window.confirm(confirmMsg)) return;

    try {
      await api.adminUpdateUserRole(targetUser.id, newRole);
      triggerHaptic?.('success');
      setUsers((prev) =>
        prev.map((u) =>
          u.id === targetUser.id
            ? { ...u, role: newRole, is_verified: newRole === 'admin' ? true : u.is_verified }
            : u
        )
      );
      onDataChanged();
    } catch (err: any) {
      triggerHaptic?.('error');
      setUserActionError(err.message || 'Failed to update user role');
    }
  };

  const unverifiedCount = users.filter((u) => !u.is_verified).length;
  const filteredUsers = users.filter(
    (u) =>
      u.first_name.toLowerCase().includes(userSearch.toLowerCase()) ||
      (u.username && u.username.toLowerCase().includes(userSearch.toLowerCase()))
  );

  const totalActivePledges = users
    .filter((u) => u.pledge_active)
    .reduce((sum, u) => sum + u.pledge_amount, 0);

  return (
    <div className="space-y-4">
      {/* Admin Sub-Navigation */}
      <div className="bg-stone-200/80 p-1 rounded-2xl flex items-center justify-between text-[11px] font-bold text-coffee-latte">
        <button
          onClick={() => {
            triggerHaptic?.('light');
            setAdminSection('operations');
          }}
          className={`flex-1 py-1.5 rounded-xl flex items-center justify-center gap-1 transition-all ${
            adminSection === 'operations'
              ? 'bg-coffee-espresso text-white shadow-sm'
              : 'hover:text-coffee-espresso'
          }`}
        >
          <span>Operations</span>
          {pendingDonations.length > 0 && (
            <span className="w-4 h-4 rounded-full bg-amber-500 text-white text-[9px] flex items-center justify-center font-bold">
              {pendingDonations.length}
            </span>
          )}
        </button>

        <button
          onClick={() => {
            triggerHaptic?.('light');
            setAdminSection('members');
          }}
          className={`flex-1 py-1.5 rounded-xl flex items-center justify-center gap-1 transition-all ${
            adminSection === 'members'
              ? 'bg-coffee-espresso text-white shadow-sm'
              : 'hover:text-coffee-espresso'
          }`}
        >
          <Users className="w-3 h-3" />
          <span>Members ({users.length})</span>
          {unverifiedCount > 0 && (
            <span className="w-4 h-4 rounded-full bg-rose-500 text-white text-[9px] flex items-center justify-center font-bold">
              {unverifiedCount}
            </span>
          )}
        </button>

        <button
          onClick={() => {
            triggerHaptic?.('light');
            setAdminSection('settings');
          }}
          className={`flex-1 py-1.5 rounded-xl flex items-center justify-center gap-1 transition-all ${
            adminSection === 'settings'
              ? 'bg-coffee-espresso text-white shadow-sm'
              : 'hover:text-coffee-espresso'
          }`}
        >
          <SettingsIcon className="w-3 h-3" />
          <span>Settings</span>
        </button>
      </div>

      {userActionError && (
        <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-2xl flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{userActionError}</span>
        </div>
      )}

      {/* SECTION 1: OPERATIONS */}
      {adminSection === 'operations' && (
        <>
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
        </>
      )}

      {/* SECTION 2: MEMBERS & ACCESS */}
      {adminSection === 'members' && (
        <div className="space-y-4">
          {/* Members Metric Overview */}
          <div className="grid grid-cols-3 gap-2">
            <div className="bg-white p-3 rounded-2xl border border-coffee-border/70 text-center">
              <span className="text-[10px] uppercase font-bold text-stone-400 block">Total</span>
              <span className="text-base font-extrabold text-coffee-espresso">{users.length}</span>
            </div>
            <div className="bg-white p-3 rounded-2xl border border-coffee-border/70 text-center">
              <span className="text-[10px] uppercase font-bold text-emerald-600 block">Verified</span>
              <span className="text-base font-extrabold text-emerald-700">
                {users.filter((u) => u.is_verified).length}
              </span>
            </div>
            <div className="bg-white p-3 rounded-2xl border border-coffee-border/70 text-center">
              <span className="text-[10px] uppercase font-bold text-amber-700 block">Pledges</span>
              <span className="text-base font-extrabold text-coffee-espresso">
                €{totalActivePledges.toFixed(0)}<span className="text-[10px] text-stone-400">/mo</span>
              </span>
            </div>
          </div>

          {/* Search box */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-stone-400 absolute left-3 top-3" />
            <input
              type="text"
              placeholder="Search members by name or @username..."
              value={userSearch}
              onChange={(e) => setUserSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-2 text-xs rounded-xl border border-stone-200 bg-white focus:outline-none focus:ring-1 focus:ring-coffee-latte text-coffee-espresso"
            />
          </div>

          {/* User List */}
          <div className="space-y-2">
            {filteredUsers.length === 0 ? (
              <div className="p-4 bg-white rounded-2xl text-center text-xs text-stone-400 border border-coffee-border/60">
                No members found matching "{userSearch}".
              </div>
            ) : (
              filteredUsers.map((member) => (
                <div
                  key={member.id}
                  className="bg-white p-3.5 rounded-2xl border border-coffee-border/70 shadow-sm space-y-2"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-1.5">
                        <span className="text-xs font-bold text-coffee-espresso">
                          {member.first_name}
                        </span>
                        {member.role === 'admin' && (
                          <span className="px-1.5 py-0.5 rounded-md bg-amber-100 text-amber-900 text-[9px] font-extrabold flex items-center gap-0.5">
                            <Crown className="w-2.5 h-2.5" />
                            Admin
                          </span>
                        )}
                        {member.is_verified ? (
                          <span className="px-1.5 py-0.5 rounded-md bg-emerald-50 text-emerald-700 border border-emerald-200 text-[9px] font-bold flex items-center gap-0.5">
                            <UserCheck className="w-2.5 h-2.5" />
                            Verified
                          </span>
                        ) : (
                          <span className="px-1.5 py-0.5 rounded-md bg-rose-50 text-rose-700 border border-rose-200 text-[9px] font-bold flex items-center gap-0.5">
                            <Clock className="w-2.5 h-2.5" />
                            Pending
                          </span>
                        )}
                      </div>
                      <div className="text-[10px] text-stone-400">
                        {member.username ? `@${member.username}` : `TG ID: ${member.tg_id}`} • Joined{' '}
                        {new Date(member.created_at).toLocaleDateString([], { month: 'short', day: 'numeric' })}
                      </div>
                    </div>

                    <div className="text-right">
                      <div className="text-xs font-extrabold text-coffee-espresso">
                        €{member.total_donated.toFixed(2)}
                      </div>
                      <div className="text-[9px] text-stone-400">
                        {member.pledge_active ? `€${member.pledge_amount.toFixed(2)}/mo` : 'No pledge'}
                      </div>
                    </div>
                  </div>

                  {/* Actions for member */}
                  <div className="pt-2 border-t border-stone-100 flex items-center justify-end gap-1.5">
                    {/* Verification Toggle */}
                    <button
                      onClick={() => handleToggleVerification(member)}
                      className={`px-2.5 py-1 rounded-lg text-[10px] font-bold transition-all flex items-center gap-1 ${
                        member.is_verified
                          ? 'bg-stone-100 hover:bg-stone-200 text-stone-600'
                          : 'bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm'
                      }`}
                    >
                      {member.is_verified ? (
                        <>
                          <UserX className="w-2.5 h-2.5" />
                          <span>Revoke Access</span>
                        </>
                      ) : (
                        <>
                          <UserCheck className="w-2.5 h-2.5" />
                          <span>Verify Member</span>
                        </>
                      )}
                    </button>

                    {/* Role Toggle */}
                    <button
                      onClick={() => handleToggleRole(member)}
                      className={`px-2.5 py-1 rounded-lg text-[10px] font-bold transition-all flex items-center gap-1 ${
                        member.role === 'admin'
                          ? 'bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200'
                          : 'bg-amber-50 hover:bg-amber-100 text-amber-900 border border-amber-200'
                      }`}
                    >
                      <Crown className="w-2.5 h-2.5" />
                      <span>{member.role === 'admin' ? 'Demote to User' : 'Promote Admin'}</span>
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* SECTION 3: COMMUNITY SETTINGS */}
      {adminSection === 'settings' && (
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
      )}
    </div>
  );
};
