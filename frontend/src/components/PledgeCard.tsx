import React, { useState, useEffect } from 'react';
import { BellRing, Check, Sparkles } from 'lucide-react';
import { User } from '../types';
import { api } from '../services/api';

interface PledgeCardProps {
  user: User | null;
  onPledgeUpdated: (user: User) => void;
  triggerHaptic?: (type: 'light' | 'success') => void;
}

const PLEDGE_OPTIONS = [5, 10, 15, 20];

export const PledgeCard: React.FC<PledgeCardProps> = ({
  user,
  onPledgeUpdated,
  triggerHaptic,
}) => {
  const [isActive, setIsActive] = useState<boolean>(user?.pledge_active ?? false);
  const [amount, setAmount] = useState<number>(user?.pledge_amount || 10);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [savedSuccess, setSavedSuccess] = useState<boolean>(false);

  useEffect(() => {
    if (user) {
      setIsActive(user.pledge_active);
      setAmount(user.pledge_amount > 0 ? user.pledge_amount : 10);
    }
  }, [user]);

  const handleSave = async (activeState = isActive, amountVal = amount) => {
    setIsSaving(true);
    try {
      const updated = await api.updatePledge(amountVal, activeState);
      triggerHaptic?.('success');
      setSavedSuccess(true);
      onPledgeUpdated(updated);
      setTimeout(() => setSavedSuccess(false), 2500);
    } catch (e) {
      console.error('Failed to update pledge:', e);
    } finally {
      setIsSaving(false);
    }
  };

  const handleToggle = () => {
    triggerHaptic?.('light');
    const nextState = !isActive;
    setIsActive(nextState);
    handleSave(nextState, amount);
  };

  const handleSelectAmount = (val: number) => {
    triggerHaptic?.('light');
    setAmount(val);
    if (isActive) {
      handleSave(isActive, val);
    }
  };

  return (
    <div className="bg-white rounded-3xl p-5 shadow-warm border border-coffee-border/70">
      <div className="flex items-start justify-between">
        <div className="flex items-center space-x-2.5">
          <div className="w-9 h-9 rounded-xl bg-amber-100/70 border border-amber-200/50 flex items-center justify-center text-amber-800">
            <BellRing className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-coffee-espresso">Monthly Soft Pledge</h3>
            <p className="text-[11px] text-stone-500">Gentle reminder on 1st of each month</p>
          </div>
        </div>

        {/* Toggle Switch */}
        <button
          type="button"
          onClick={handleToggle}
          className={`w-12 h-6 flex items-center rounded-full p-1 transition-colors duration-300 ${
            isActive ? 'bg-coffee-espresso' : 'bg-stone-300'
          }`}
        >
          <div
            className={`bg-white w-4 h-4 rounded-full shadow-md transform transition-transform duration-300 ${
              isActive ? 'translate-x-6' : 'translate-x-0'
            }`}
          />
        </button>
      </div>

      <p className="text-xs text-stone-600 mt-3 leading-relaxed">
        Support the coffee pot effortlessly. When active, the Telegram bot pings you on the 1st with
        direct buttons to pay or skip.
      </p>

      {isActive && (
        <div className="mt-4 pt-3 border-t border-coffee-border/40">
          <label className="block text-[11px] font-semibold text-coffee-latte uppercase tracking-wider mb-2">
            Pledge Amount
          </label>
          <div className="grid grid-cols-4 gap-2">
            {PLEDGE_OPTIONS.map((val) => (
              <button
                key={val}
                type="button"
                onClick={() => handleSelectAmount(val)}
                className={`py-2 px-3 rounded-xl text-xs font-bold transition-all ${
                  amount === val
                    ? 'bg-coffee-espresso text-white shadow-sm'
                    : 'bg-stone-50 text-stone-700 border border-stone-200 hover:border-stone-300'
                }`}
              >
                €{val}
              </button>
            ))}
          </div>

          <div className="flex items-center justify-between mt-3 text-xs">
            <span className="text-stone-500 flex items-center gap-1">
              <Sparkles className="w-3.5 h-3.5 text-amber-500" />
              Pledged: <strong className="text-coffee-espresso">€{amount.toFixed(2)}/mo</strong>
            </span>
            {isSaving ? (
              <span className="text-coffee-latte font-medium text-[11px]">Saving...</span>
            ) : savedSuccess ? (
              <span className="text-emerald-700 font-semibold flex items-center gap-1 text-[11px]">
                <Check className="w-3 h-3" /> Saved!
              </span>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
};
