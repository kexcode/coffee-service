import React, { useState, useEffect } from 'react';
import { X, Check, Trash2, Edit3, AlertCircle } from 'lucide-react';
import { FeedItem, ExpensePayload, AdminUser } from '../types';
import { api } from '../services/api';

interface EditEntryModalProps {
  entry: FeedItem | null;
  isOpen: boolean;
  onClose: () => void;
  onSaved: () => void;
  triggerHaptic?: (type: 'light' | 'success' | 'error') => void;
}

const EXPENSE_CATEGORIES: { key: ExpensePayload['category']; label: string }[] = [
  { key: 'beans', label: '☕ Coffee Beans' },
  { key: 'sweets', label: '🍪 Sweets & Snacks' },
  { key: 'filters', label: '📄 Paper & Filters' },
  { key: 'cleaning', label: '🧼 Cleaning & Descaling' },
  { key: 'maintenance_repair', label: '🔧 Maintenance & Parts' },
  { key: 'depreciation_reserve', label: '🏦 Equipment Reserve' },
];

export const EditEntryModal: React.FC<EditEntryModalProps> = ({
  entry,
  isOpen,
  onClose,
  onSaved,
  triggerHaptic,
}) => {
  if (!isOpen || !entry) return null;

  const isExpense = entry.type === 'expense';

  // Expense form state
  const [category, setCategory] = useState<ExpensePayload['category']>(
    (entry.category as ExpensePayload['category']) || 'beans'
  );
  const [amount, setAmount] = useState<string>(entry.amount.toFixed(2));
  const [description, setDescription] = useState<string>(entry.description);
  const [receiptUrl, setReceiptUrl] = useState<string>(entry.receipt_url || '');

  // Donation form state
  const [paymentMethod, setPaymentMethod] = useState<string>(entry.payment_method || 'cash');
  const [donationStatus, setDonationStatus] = useState<string>(entry.status || 'confirmed');
  const [selectedUserId, setSelectedUserId] = useState<number | undefined>(entry.user_id || undefined);
  const [users, setUsers] = useState<AdminUser[]>([]);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      api.adminGetUsers()
        .then((data) => setUsers(data))
        .catch((err) => console.error('Failed to load users for modal:', err));
    }
  }, [isOpen]);

  useEffect(() => {
    if (entry) {
      setAmount(entry.amount.toFixed(2));
      setDescription(entry.description);
      setReceiptUrl(entry.receipt_url || '');
      if (entry.type === 'expense') {
        setCategory((entry.category as ExpensePayload['category']) || 'beans');
      } else {
        setPaymentMethod(entry.payment_method || 'cash');
        setDonationStatus(entry.status || 'confirmed');
        setSelectedUserId(entry.user_id || undefined);
      }
      setConfirmDelete(false);
      setError(null);
    }
  }, [entry]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    const parsedAmount = parseFloat(amount);
    if (isNaN(parsedAmount) || parsedAmount <= 0) {
      setError('Please provide a valid positive amount.');
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      if (isExpense) {
        await api.adminUpdateExpense(entry.id, {
          category,
          amount: parsedAmount,
          description: description.trim(),
          receipt_url: receiptUrl.trim() || undefined,
        });
      } else {
        await api.adminUpdateDonation(entry.id, {
          amount: parsedAmount,
          payment_method: paymentMethod,
          status: donationStatus,
          user_id: selectedUserId,
        });
      }
      triggerHaptic?.('success');
      onSaved();
      onClose();
    } catch (err: any) {
      triggerHaptic?.('error');
      setError(err.message || 'Failed to update entry');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!confirmDelete) {
      setConfirmDelete(true);
      return;
    }

    setIsDeleting(true);
    setError(null);
    try {
      if (isExpense) {
        await api.adminDeleteExpense(entry.id);
      } else {
        await api.adminDeleteDonation(entry.id);
      }
      triggerHaptic?.('success');
      onSaved();
      onClose();
    } catch (err: any) {
      triggerHaptic?.('error');
      setError(err.message || 'Failed to delete entry');
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fadeIn">
      <div className="bg-white rounded-3xl w-full max-w-sm p-6 shadow-warm-lg border border-coffee-border relative overflow-hidden">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 w-8 h-8 rounded-full bg-stone-100 hover:bg-stone-200 text-stone-600 flex items-center justify-center transition-colors"
        >
          <X className="w-4 h-4" />
        </button>

        <div className="flex items-center space-x-2.5 mb-4">
          <div className="w-10 h-10 rounded-2xl bg-amber-100 text-coffee-espresso flex items-center justify-center">
            <Edit3 className="w-5 h-5 text-amber-800" />
          </div>
          <div>
            <h2 className="text-base font-bold text-coffee-espresso">
              Edit {isExpense ? 'Expense Entry' : 'Donation Entry'}
            </h2>
            <p className="text-[11px] text-stone-500">Correct details or remove record</p>
          </div>
        </div>

        {error && (
          <div className="mb-3 p-2.5 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-xl flex items-center gap-1.5">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSave} className="space-y-3">
          {/* Amount field */}
          <div>
            <label className="block text-[11px] font-semibold text-coffee-latte uppercase tracking-wider mb-1">
              Amount (€)
            </label>
            <input
              type="number"
              step="0.01"
              min="0.1"
              required
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="w-full text-xs font-bold p-2.5 rounded-xl border border-stone-200 bg-stone-50 focus:bg-white focus:outline-none focus:ring-1 focus:ring-coffee-latte text-coffee-espresso"
            />
          </div>

          {/* If Expense: category, description, receipt */}
          {isExpense ? (
            <>
              <div>
                <label className="block text-[11px] font-semibold text-coffee-latte uppercase tracking-wider mb-1">
                  Category
                </label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value as ExpensePayload['category'])}
                  className="w-full text-xs font-semibold p-2.5 rounded-xl border border-stone-200 bg-stone-50 focus:bg-white text-coffee-espresso"
                >
                  {EXPENSE_CATEGORIES.map((cat) => (
                    <option key={cat.key} value={cat.key}>
                      {cat.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-coffee-latte uppercase tracking-wider mb-1">
                  Description
                </label>
                <input
                  type="text"
                  required
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full text-xs p-2.5 rounded-xl border border-stone-200 bg-stone-50 focus:bg-white text-coffee-espresso"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-coffee-latte uppercase tracking-wider mb-1">
                  Receipt URL (Optional)
                </label>
                <input
                  type="url"
                  placeholder="https://..."
                  value={receiptUrl}
                  onChange={(e) => setReceiptUrl(e.target.value)}
                  className="w-full text-xs p-2.5 rounded-xl border border-stone-200 bg-stone-50 focus:bg-white text-coffee-espresso"
                />
              </div>
            </>
          ) : (
            /* If Donation: donor name, payment method, status */
            <>
              <div>
                <label className="block text-[11px] font-semibold text-coffee-latte uppercase tracking-wider mb-1">
                  Contributor
                </label>
                <select
                  value={selectedUserId || ''}
                  onChange={(e) => setSelectedUserId(e.target.value ? Number(e.target.value) : undefined)}
                  className="w-full text-xs font-semibold p-2.5 rounded-xl border border-stone-200 bg-stone-50 focus:bg-white text-coffee-espresso"
                >
                  {users.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.tg_id === 0 ? '🎭 Anonymous / Cash Jar' : `${u.first_name} ${u.username ? `(@${u.username})` : ''}`}
                    </option>
                  ))}
                  {selectedUserId && !users.some((u) => u.id === selectedUserId) && (
                    <option value={selectedUserId}>
                      {entry.actor_name} {entry.actor_username ? `(@${entry.actor_username})` : ''}
                    </option>
                  )}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-[11px] font-semibold text-coffee-latte uppercase tracking-wider mb-1">
                    Method
                  </label>
                  <select
                    value={paymentMethod}
                    onChange={(e) => setPaymentMethod(e.target.value)}
                    className="w-full text-xs font-semibold p-2.5 rounded-xl border border-stone-200 bg-stone-50 text-coffee-espresso"
                  >
                    <option value="cash">Cash Jar</option>
                    <option value="paypal">PayPal</option>
                    <option value="card">Card</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-coffee-latte uppercase tracking-wider mb-1">
                    Status
                  </label>
                  <select
                    value={donationStatus}
                    onChange={(e) => setDonationStatus(e.target.value)}
                    className="w-full text-xs font-semibold p-2.5 rounded-xl border border-stone-200 bg-stone-50 text-coffee-espresso"
                  >
                    <option value="confirmed">Confirmed</option>
                    <option value="pending">Pending</option>
                    <option value="rejected">Rejected</option>
                  </select>
                </div>
              </div>
            </>
          )}

          {/* Action buttons */}
          <div className="pt-2 space-y-2">
            <button
              type="submit"
              disabled={isSubmitting || isDeleting}
              className="w-full py-2.5 bg-coffee-espresso hover:bg-coffee-roast text-white rounded-xl font-bold text-xs flex items-center justify-center gap-1.5 shadow-sm transition-all disabled:opacity-50"
            >
              <Check className="w-3.5 h-3.5" />
              <span>{isSubmitting ? 'Saving...' : 'Save Changes'}</span>
            </button>

            <button
              type="button"
              onClick={handleDelete}
              disabled={isSubmitting || isDeleting}
              className={`w-full py-2.5 rounded-xl font-bold text-xs flex items-center justify-center gap-1.5 transition-all disabled:opacity-50 ${
                confirmDelete
                  ? 'bg-rose-600 text-white'
                  : 'bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200'
              }`}
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>
                {isDeleting
                  ? 'Deleting...'
                  : confirmDelete
                  ? 'Confirm Delete Permanently?'
                  : 'Delete Entry'}
              </span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
