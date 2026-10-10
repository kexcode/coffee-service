import React from 'react';
import { Coffee, ExternalLink } from 'lucide-react';

interface QuickActionsProps {
  onOpenContribute: () => void;
  paypalUrl: string;
  openLink: (url: string) => void;
  triggerHaptic?: (type: 'light' | 'medium') => void;
}

export const QuickActions: React.FC<QuickActionsProps> = ({
  onOpenContribute,
  paypalUrl,
  openLink,
  triggerHaptic,
}) => {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
      <button
        onClick={() => {
          triggerHaptic?.('medium');
          onOpenContribute();
        }}
        className="w-full py-3.5 px-4 bg-coffee-espresso hover:bg-coffee-roast active:scale-[0.98] text-white rounded-2xl font-bold text-sm flex items-center justify-center gap-2 shadow-warm transition-all"
      >
        <Coffee className="w-4 h-4 text-amber-400" />
        <span>Contribute to Coffee Pot</span>
      </button>

      <button
        onClick={() => {
          triggerHaptic?.('light');
          openLink(paypalUrl);
        }}
        className="w-full py-3.5 px-4 bg-white hover:bg-coffee-cream active:scale-[0.98] border border-coffee-border text-coffee-espresso rounded-2xl font-semibold text-xs flex items-center justify-center gap-2 shadow-sm transition-all"
      >
        <span className="text-sky-700 font-bold">PayPal.me</span>
        <span className="text-stone-500">Quick link</span>
        <ExternalLink className="w-3.5 h-3.5 text-stone-400 ml-0.5" />
      </button>
    </div>
  );
};
