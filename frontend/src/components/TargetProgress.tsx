import React from 'react';
import { TrendingUp, ArrowDownRight, ArrowUpRight, Sparkles } from 'lucide-react';
import { DashboardData } from '../types';

interface TargetProgressProps {
  data: DashboardData | null;
}

export const TargetProgress: React.FC<TargetProgressProps> = ({ data }) => {
  const balance = data?.total_balance ?? 0;
  const target = data?.monthly_target ?? 150;
  const collected = data?.monthly_collected ?? 0;
  const expenses = data?.monthly_expenses ?? 0;

  const progressPercent = Math.min(Math.round((collected / (target || 1)) * 100), 100);
  const isTargetMet = collected >= target;

  return (
    <div className="bg-white rounded-3xl p-5 shadow-warm border border-coffee-border/70 relative overflow-hidden">
      {/* Decorative background glow */}
      <div className="absolute -top-12 -right-12 w-32 h-32 bg-amber-100 rounded-full blur-2xl pointer-events-none opacity-60" />

      {/* Treasury Balance Readout */}
      <div className="flex flex-col items-center justify-center text-center pb-5 pt-1">
        <span className="text-xs font-semibold uppercase tracking-wider text-coffee-latte flex items-center gap-1">
          <Sparkles className="w-3.5 h-3.5 text-amber-500" />
          Treasury Pot Balance
        </span>
        <div className="flex items-baseline mt-1 space-x-1">
          <span className="text-4xl font-extrabold text-coffee-espresso tracking-tight">
            €{balance.toFixed(2)}
          </span>
        </div>
        <p className="text-xs text-stone-500 mt-1">
          {balance >= 20 ? (
            <span className="text-emerald-700 font-medium">● Healthy pot — beans in stock!</span>
          ) : balance > 0 ? (
            <span className="text-amber-700 font-medium">● Low reserve — consider pitching in</span>
          ) : (
            <span className="text-rose-700 font-medium">● Pot empty — needs refills soon!</span>
          )}
        </p>
      </div>

      {/* Monthly Target Progress Meter */}
      <div className="bg-coffee-cream/80 rounded-2xl p-4 border border-coffee-border/50">
        <div className="flex items-center justify-between text-xs mb-2">
          <span className="font-semibold text-coffee-roast flex items-center gap-1.5">
            <TrendingUp className="w-4 h-4 text-coffee-caramel" />
            Monthly Goal
          </span>
          <span className="font-bold text-coffee-espresso">
            €{collected.toFixed(2)} <span className="text-coffee-latte font-normal">/ €{target.toFixed(2)}</span>
          </span>
        </div>

        {/* Progress Bar */}
        <div className="w-full h-3 bg-stone-200 rounded-full overflow-hidden relative">
          <div
            className={`h-full transition-all duration-700 ease-out rounded-full ${
              isTargetMet ? 'bg-emerald-500' : 'bg-gradient-to-r from-coffee-latte to-amber-500'
            }`}
            style={{ width: `${progressPercent}%` }}
          />
        </div>

        <div className="flex items-center justify-between text-[11px] text-coffee-latte mt-2">
          <span>{progressPercent}% funded</span>
          <span>
            {isTargetMet ? (
              <strong className="text-emerald-700">Goal reached! 🎉</strong>
            ) : (
              `€${(target - collected).toFixed(2)} remaining`
            )}
          </span>
        </div>
      </div>

      {/* Quick Monthly Stats */}
      <div className="grid grid-cols-2 gap-3 mt-3 text-xs">
        <div className="bg-emerald-50/70 border border-emerald-100 rounded-xl p-2.5 flex items-center space-x-2">
          <div className="w-7 h-7 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center shrink-0">
            <ArrowUpRight className="w-4 h-4" />
          </div>
          <div>
            <div className="text-[10px] text-emerald-800 uppercase font-bold tracking-wider">Collected</div>
            <div className="font-bold text-emerald-950">€{collected.toFixed(2)}</div>
          </div>
        </div>

        <div className="bg-stone-50 border border-stone-200/80 rounded-xl p-2.5 flex items-center space-x-2">
          <div className="w-7 h-7 rounded-lg bg-stone-200 text-coffee-dark flex items-center justify-center shrink-0">
            <ArrowDownRight className="w-4 h-4" />
          </div>
          <div>
            <div className="text-[10px] text-stone-600 uppercase font-bold tracking-wider">Spent</div>
            <div className="font-bold text-coffee-espresso">€{expenses.toFixed(2)}</div>
          </div>
        </div>
      </div>
    </div>
  );
};
