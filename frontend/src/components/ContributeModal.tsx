import React, { useState } from 'react';
import { X, CheckCircle, ExternalLink, Banknote, HeartHandshake } from 'lucide-react';
import { api } from '../services/api';

interface ContributeModalProps {
  isOpen: boolean;
  onClose: () => void;
  paypalUrl: string;
  onSuccess: () => void;
  triggerHaptic?: (type: 'light' | 'medium' | 'heavy' | 'success' | 'warning' | 'error') => void;
  openLink: (url: string) => void;
}

const PRESET_AMOUNTS = [
  { value: 5, label: '€5', desc: 'Espresso Lover' },
  { value: 10, label: '€10', desc: 'Office Regular' },
  { value: 15, label: '€15', desc: 'Specialty Roast' },
  { value: 20, label: '€20', desc: 'Coffee Hero' },
];

export const ContributeModal: React.FC<ContributeModalProps> = ({
  isOpen,
  onClose,
  paypalUrl,
  onSuccess,
  triggerHaptic,
  openLink,
}) => {
  const [selectedAmount, setSelectedAmount] = useState<number>(10);
  const [customAmount, setCustomAmount] = useState<string>('');
  const [isCustom, setIsCustom] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [cashSuccess, setCashSuccess] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const getEffectiveAmount = (): number => {
    if (isCustom) {
      const val = parseFloat(customAmount);
      return isNaN(val) || val <= 0 ? 0 : val;
    }
    return selectedAmount;
  };

  const handlePayPal = () => {
    const amount = getEffectiveAmount();
    if (amount <= 0) {
      setError('Please select or enter a valid amount.');
      return;
    }
    triggerHaptic?.('medium');
    let targetUrl = paypalUrl;
    if (paypalUrl.includes('paypal.me')) {
      targetUrl = `${paypalUrl.replace(/\/$/, '')}/${amount}EUR`;
    }
    openLink(targetUrl);
  };

  const handleCash = async () => {
    const amount = getEffectiveAmount();
    if (amount <= 0) {
      setError('Please select or enter a valid positive amount.');
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      await api.submitCashDonation(amount);
      triggerHaptic?.('success');
      setCashSuccess(true);
      onSuccess();
    } catch (e: any) {
      triggerHaptic?.('error');
      setError(e.message || 'Failed to record cash payment');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setCashSuccess(false);
    setError(null);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fadeIn">
      <div className="bg-white rounded-3xl w-full max-w-sm p-6 shadow-warm-lg border border-coffee-border relative overflow-hidden">
        {/* Close Button */}
        <button
          onClick={handleClose}
          className="absolute top-4 right-4 w-8 h-8 rounded-full bg-stone-100 hover:bg-stone-200 text-stone-600 flex items-center justify-center transition-colors"
        >
          <X className="w-4 h-4" />
        </button>

        {cashSuccess ? (
          <div className="text-center py-4">
            <div className="w-16 h-16 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto mb-4">
              <CheckCircle className="w-8 h-8" />
            </div>
            <h3 className="text-lg font-bold text-coffee-espresso">Cash Contribution Logged!</h3>
            <p className="text-xs text-stone-600 mt-2 leading-relaxed">
              We logged your <strong className="text-coffee-espresso">€{getEffectiveAmount().toFixed(2)}</strong> cash donation.
              Please drop the coins/cash into the coffee box. An admin has been notified in Telegram to verify it.
            </p>
            <button
              onClick={handleClose}
              className="mt-6 w-full py-3 bg-coffee-espresso text-white rounded-2xl font-semibold text-sm hover:bg-coffee-roast active:scale-[0.98] transition-all"
            >
              Done & Return to Pot
            </button>
          </div>
        ) : (
          <div>
            <div className="text-center mb-5">
              <div className="w-12 h-12 rounded-2xl bg-amber-100 text-coffee-espresso flex items-center justify-center mx-auto mb-2">
                <HeartHandshake className="w-6 h-6 text-amber-700" />
              </div>
              <h2 className="text-lg font-bold text-coffee-espresso">Support Our Coffee Pot</h2>
              <p className="text-xs text-stone-500 mt-0.5">Community-funded fresh specialty beans</p>
            </div>

            {error && (
              <div className="mb-4 p-2.5 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-xl">
                {error}
              </div>
            )}

            {/* Amount Selection Grid */}
            <div className="mb-4">
              <label className="block text-xs font-semibold text-stone-600 mb-2">Select Amount</label>
              <div className="grid grid-cols-2 gap-2">
                {PRESET_AMOUNTS.map((item) => (
                  <button
                    key={item.value}
                    type="button"
                    onClick={() => {
                      setSelectedAmount(item.value);
                      setIsCustom(false);
                      triggerHaptic?.('light');
                    }}
                    className={`p-3 rounded-2xl border text-left transition-all ${
                      !isCustom && selectedAmount === item.value
                        ? 'border-coffee-espresso bg-coffee-cream shadow-sm font-semibold'
                        : 'border-stone-200 hover:border-stone-300 bg-stone-50/50'
                    }`}
                  >
                    <div className="text-base font-extrabold text-coffee-espresso">{item.label}</div>
                    <div className="text-[10px] text-coffee-latte mt-0.5">{item.desc}</div>
                  </button>
                ))}
              </div>

              {/* Custom Amount Field */}
              <div className="mt-2.5">
                <div
                  onClick={() => setIsCustom(true)}
                  className={`flex items-center px-3.5 py-2.5 rounded-2xl border ${
                    isCustom
                      ? 'border-coffee-espresso bg-white ring-2 ring-coffee-latte/20'
                      : 'border-stone-200 bg-stone-50/50'
                  }`}
                >
                  <span className="text-xs text-stone-500 font-medium mr-2">Custom €</span>
                  <input
                    type="number"
                    step="0.5"
                    min="1"
                    placeholder="Other amount"
                    value={customAmount}
                    onChange={(e) => {
                      setCustomAmount(e.target.value);
                      setIsCustom(true);
                    }}
                    className="w-full text-sm font-bold bg-transparent outline-none text-coffee-espresso"
                  />
                </div>
              </div>
            </div>

            {/* Payment Methods */}
            <div className="space-y-2.5 pt-2">
              <button
                type="button"
                onClick={handlePayPal}
                className="w-full py-3 px-4 bg-sky-600 hover:bg-sky-700 active:scale-[0.98] text-white rounded-2xl font-bold text-xs flex items-center justify-center gap-2 shadow-sm transition-all"
              >
                <span>Pay €{getEffectiveAmount().toFixed(2)} via PayPal</span>
                <ExternalLink className="w-3.5 h-3.5 opacity-80" />
              </button>

              <button
                type="button"
                onClick={handleCash}
                disabled={isSubmitting}
                className="w-full py-3 px-4 bg-coffee-cream hover:bg-coffee-paper active:scale-[0.98] border border-coffee-border text-coffee-espresso rounded-2xl font-bold text-xs flex items-center justify-center gap-2 transition-all disabled:opacity-50"
              >
                <Banknote className="w-4 h-4 text-emerald-700" />
                <span>
                  {isSubmitting
                    ? 'Logging...'
                    : `I Dropped €${getEffectiveAmount().toFixed(2)} in Cash Jar`}
                </span>
              </button>
            </div>

            <p className="text-[11px] text-center text-stone-400 mt-3">
              Trust-based community tracking with admin review
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
