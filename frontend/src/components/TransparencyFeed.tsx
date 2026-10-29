import React, { useState } from 'react';
import { ArrowUpRight, ArrowDownRight, FileText, ExternalLink, Calendar, Edit2, Lock } from 'lucide-react';
import { FeedItem } from '../types';

interface TransparencyFeedProps {
  items: FeedItem[];
  openLink: (url: string) => void;
  isAdmin?: boolean;
  isVerified?: boolean;
  onEditEntry?: (item: FeedItem) => void;
}

export const TransparencyFeed: React.FC<TransparencyFeedProps> = ({
  items,
  openLink,
  isAdmin,
  isVerified = true,
  onEditEntry,
}) => {
  const [filter, setFilter] = useState<'all' | 'donation' | 'expense'>('all');

  if (!isVerified) {
    return (
      <div className="bg-white rounded-3xl p-6 shadow-warm border border-amber-200/80 text-center">
        <div className="w-12 h-12 rounded-2xl bg-amber-100 text-amber-800 flex items-center justify-center mx-auto mb-3">
          <Lock className="w-6 h-6" />
        </div>
        <h3 className="text-sm font-bold text-coffee-espresso">Transparency Audit Gated</h3>
        <p className="text-xs text-stone-500 mt-1 max-w-xs mx-auto">
          The live transaction audit and expense logs are only visible to verified community members. Ask an admin to verify your account to view the feed.
        </p>
      </div>
    );
  }

  const filteredItems = items.filter((item) => {
    if (filter === 'all') return true;
    return item.type === filter;
  });

  const formatDate = (isoStr: string) => {
    try {
      const d = new Date(isoStr);
      return d.toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return isoStr;
    }
  };

  return (
    <div className="bg-white rounded-3xl p-5 shadow-warm border border-coffee-border/70">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-bold text-coffee-espresso">Transparency Audit</h3>
          <p className="text-[11px] text-stone-500">Every cup and cent accounted for</p>
        </div>

        {/* Filter Pills */}
        <div className="flex bg-stone-100 p-1 rounded-xl text-[11px]">
          <button
            onClick={() => setFilter('all')}
            className={`px-2.5 py-1 rounded-lg font-semibold transition-all ${
              filter === 'all' ? 'bg-white text-coffee-espresso shadow-sm' : 'text-stone-500'
            }`}
          >
            All
          </button>
          <button
            onClick={() => setFilter('donation')}
            className={`px-2.5 py-1 rounded-lg font-semibold transition-all ${
              filter === 'donation' ? 'bg-white text-coffee-espresso shadow-sm' : 'text-stone-500'
            }`}
          >
            In
          </button>
          <button
            onClick={() => setFilter('expense')}
            className={`px-2.5 py-1 rounded-lg font-semibold transition-all ${
              filter === 'expense' ? 'bg-white text-coffee-espresso shadow-sm' : 'text-stone-500'
            }`}
          >
            Out
          </button>
        </div>
      </div>

      {filteredItems.length === 0 ? (
        <div className="text-center py-8 text-xs text-stone-400">
          No transactions found under this filter.
        </div>
      ) : (
        <div className="divide-y divide-stone-100 max-h-96 overflow-y-auto pr-1">
          {filteredItems.map((item) => {
            const isDonation = item.type === 'donation';

            return (
              <div key={`${item.type}-${item.id}`} className="py-3 flex items-start justify-between gap-3">
                <div className="flex items-start space-x-3">
                  <div
                    className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 mt-0.5 ${
                      isDonation
                        ? 'bg-emerald-100 text-emerald-700'
                        : 'bg-stone-200 text-coffee-dark'
                    }`}
                  >
                    {isDonation ? (
                      <ArrowUpRight className="w-4 h-4" />
                    ) : (
                      <ArrowDownRight className="w-4 h-4" />
                    )}
                  </div>

                  <div>
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className="text-xs font-bold text-coffee-espresso">
                        {item.actor_name}
                      </span>
                      {item.payment_method && (
                        <span className="px-1.5 py-0.2 rounded-md bg-stone-100 text-stone-600 text-[10px] uppercase font-semibold">
                          {item.payment_method === 'cash' ? 'Cash Jar' : item.payment_method}
                        </span>
                      )}
                      {item.category && (
                        <span className="px-1.5 py-0.2 rounded-md bg-amber-100 text-amber-800 text-[10px] font-semibold">
                          {item.category.replace('_', ' ')}
                        </span>
                      )}
                    </div>

                    <p className="text-xs text-stone-600 mt-0.5 leading-snug">{item.description}</p>

                    <div className="flex items-center gap-2 mt-1 text-[10px] text-stone-400">
                      <span className="flex items-center gap-0.5">
                        <Calendar className="w-2.5 h-2.5" />
                        {formatDate(item.created_at)}
                      </span>
                      {item.receipt_url && (
                        <button
                          onClick={() => openLink(item.receipt_url!)}
                          className="text-coffee-latte hover:text-coffee-espresso flex items-center gap-0.5 font-medium underline"
                        >
                          <FileText className="w-2.5 h-2.5" />
                          Receipt
                          <ExternalLink className="w-2 h-2 ml-0.5" />
                        </button>
                      )}
                    </div>
                  </div>
                </div>

                <div className="text-right shrink-0 flex items-center space-x-1.5">
                  <span
                    className={`text-xs font-extrabold ${
                      isDonation ? 'text-emerald-700' : 'text-coffee-espresso'
                    }`}
                  >
                    {isDonation ? `+€${item.amount.toFixed(2)}` : `-€${item.amount.toFixed(2)}`}
                  </span>
                  {isAdmin && onEditEntry && (
                    <button
                      onClick={() => onEditEntry(item)}
                      className="p-1 rounded-lg text-stone-400 hover:text-coffee-espresso hover:bg-stone-100 transition-colors"
                      title="Edit or Delete entry"
                    >
                      <Edit2 className="w-3 h-3" />
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
