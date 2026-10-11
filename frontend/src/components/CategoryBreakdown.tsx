import React from 'react';
import { Coffee, FileText, Sparkles, Wrench, Landmark, Lock } from 'lucide-react';
import { DashboardData } from '../types';

interface CategoryBreakdownProps {
  data: DashboardData | null;
}

interface CategoryMeta {
  key: string;
  name: string;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  barColor: string;
}

const CATEGORIES: CategoryMeta[] = [
  { key: 'beans', name: 'Coffee Beans', icon: Coffee, color: 'text-amber-800 bg-amber-100', barColor: 'bg-amber-600' },
  { key: 'filters', name: 'Filters & Paper', icon: FileText, color: 'text-stone-700 bg-stone-200', barColor: 'bg-stone-500' },
  { key: 'cleaning', name: 'Cleaning & Descale', icon: Sparkles, color: 'text-cyan-800 bg-cyan-100', barColor: 'bg-cyan-600' },
  { key: 'maintenance_repair', name: 'Maintenance & Parts', icon: Wrench, color: 'text-orange-800 bg-orange-100', barColor: 'bg-orange-500' },
  { key: 'depreciation_reserve', name: 'Equipment Reserve', icon: Landmark, color: 'text-indigo-800 bg-indigo-100', barColor: 'bg-indigo-600' },
];

export const CategoryBreakdown: React.FC<CategoryBreakdownProps> = ({ data }) => {
  if (data && !data.is_verified) {
    return (
      <div className="bg-white rounded-3xl p-6 shadow-warm border border-amber-200/80 text-center">
        <div className="w-12 h-12 rounded-2xl bg-amber-100 text-amber-800 flex items-center justify-center mx-auto mb-3">
          <Lock className="w-6 h-6" />
        </div>
        <h3 className="text-sm font-bold text-coffee-espresso">Spend Distribution Gated</h3>
        <p className="text-xs text-stone-500 mt-1 max-w-xs mx-auto">
          Detailed itemized breakdowns of beans, filters, and repairs are restricted to verified members.
        </p>
      </div>
    );
  }

  const breakdown = data?.category_breakdown || {};
  const totalSpent = data?.total_expenses || 0;

  return (
    <div className="bg-white rounded-3xl p-5 shadow-warm border border-coffee-border/70">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-bold text-coffee-espresso">Spend Distribution</h3>
          <p className="text-[11px] text-stone-500">All-time expenses by category</p>
        </div>
        <div className="text-right">
          <div className="text-xs font-extrabold text-coffee-espresso">€{totalSpent.toFixed(2)}</div>
          <div className="text-[10px] text-stone-400">Total Spent</div>
        </div>
      </div>

      {/* Horizontal Multi-color Stacked Bar */}
      {totalSpent > 0 ? (
        <div className="w-full h-3 rounded-full bg-stone-100 overflow-hidden flex mb-4 shadow-inner">
          {CATEGORIES.map((cat) => {
            const amount = breakdown[cat.key] || 0;
            const pct = (amount / totalSpent) * 100;
            if (pct <= 0) return null;
            return (
              <div
                key={cat.key}
                style={{ width: `${pct}%` }}
                className={`${cat.barColor} h-full transition-all duration-500`}
                title={`${cat.name}: €${amount.toFixed(2)} (${pct.toFixed(0)}%)`}
              />
            );
          })}
        </div>
      ) : (
        <div className="text-center py-4 text-xs text-stone-400 bg-stone-50 rounded-2xl mb-4">
          No expenses recorded yet. Treasury is fresh! ☕
        </div>
      )}

      {/* Categories List */}
      <div className="space-y-2.5">
        {CATEGORIES.map((cat) => {
          const amount = breakdown[cat.key] || 0;
          const percentage = totalSpent > 0 ? ((amount / totalSpent) * 100).toFixed(0) : '0';
          const Icon = cat.icon;

          return (
            <div
              key={cat.key}
              className="flex items-center justify-between p-2.5 rounded-2xl bg-stone-50/70 border border-stone-100 hover:bg-stone-50 transition-colors"
            >
              <div className="flex items-center space-x-2.5">
                <div className={`w-8 h-8 rounded-xl ${cat.color} flex items-center justify-center shrink-0`}>
                  <Icon className="w-4 h-4" />
                </div>
                <div>
                  <div className="text-xs font-bold text-coffee-espresso">{cat.name}</div>
                  <div className="text-[10px] text-stone-400">{percentage}% of expenditures</div>
                </div>
              </div>

              <div className="text-right">
                <span className="text-xs font-bold text-coffee-espresso">€{amount.toFixed(2)}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
