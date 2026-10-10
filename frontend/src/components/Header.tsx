import React from 'react';
import { Coffee, ShieldCheck, User as UserIcon, RefreshCw } from 'lucide-react';
import { User } from '../types';

interface HeaderProps {
  user: User | null;
  onRefresh: () => void;
  isLoading: boolean;
  onToggleDevRole?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  user,
  onRefresh,
  isLoading,
  onToggleDevRole,
}) => {
  return (
    <header className="bg-coffee-espresso text-coffee-cream px-4 pt-5 pb-6 rounded-b-3xl shadow-warm border-b border-coffee-roast">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2.5">
          <div className="w-10 h-10 rounded-2xl bg-coffee-latte/20 border border-coffee-latte/40 flex items-center justify-center text-coffee-caramel shadow-inner">
            <Coffee className="w-5 h-5 text-amber-300" />
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight text-white flex items-center gap-1.5">
              Office Coffee Pot
            </h1>
            <p className="text-xs text-coffee-foam font-medium">Shared Treasury & Transparency</p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          {onToggleDevRole && (
            <button
              onClick={onToggleDevRole}
              title="Toggle Dev Admin Role"
              className="text-[10px] bg-coffee-roast text-coffee-foam hover:text-white px-2 py-1 rounded-lg border border-coffee-latte/30 transition-colors"
            >
              Role: {user?.role === 'admin' ? '👑 Admin' : '👤 User'}
            </button>
          )}

          <button
            onClick={onRefresh}
            disabled={isLoading}
            className="w-9 h-9 rounded-xl bg-white/10 hover:bg-white/15 flex items-center justify-center text-coffee-cream transition-all active:scale-95 disabled:opacity-50"
            title="Refresh Data"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      <div className="flex items-center justify-between pt-2 border-t border-white/10 text-xs">
        <div className="flex items-center space-x-1.5 text-coffee-foam">
          <UserIcon className="w-3.5 h-3.5" />
          <span>
            Welcome, <strong className="text-white font-semibold">{user?.first_name || 'Coffee Lover'}</strong>
          </span>
        </div>
        <div>
          {user?.role === 'admin' ? (
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold bg-amber-400/20 text-amber-300 border border-amber-400/30">
              <ShieldCheck className="w-3 h-3 mr-1" />
              Coffee Steward
            </span>
          ) : (
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-white/10 text-coffee-foam">
              Community Member
            </span>
          )}
        </div>
      </div>
    </header>
  );
};
