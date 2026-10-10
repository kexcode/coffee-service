import { useState, useEffect, useCallback } from 'react';
import { Coffee, PieChart, History, Shield, AlertCircle } from 'lucide-react';
import { useTelegram } from './hooks/useTelegram';
import { setApiAuth, api } from './services/api';
import { User, DashboardData, FeedItem } from './types';
import { Header } from './components/Header';
import { TargetProgress } from './components/TargetProgress';
import { QuickActions } from './components/QuickActions';
import { ContributeModal } from './components/ContributeModal';
import { PledgeCard } from './components/PledgeCard';
import { CategoryBreakdown } from './components/CategoryBreakdown';
import { TransparencyFeed } from './components/TransparencyFeed';
import { AdminPanel } from './components/AdminPanel';

export function App() {
  const { initData, tgUser, triggerHaptic, openLink, isTma } = useTelegram();

  const [activeTab, setActiveTab] = useState<'treasury' | 'spend' | 'audit' | 'admin'>('treasury');
  const [user, setUser] = useState<User | null>(null);
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [feed, setFeed] = useState<FeedItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isContributeModalOpen, setIsContributeModalOpen] = useState<boolean>(false);
  const [devRole, setDevRole] = useState<'user' | 'admin'>('admin');

  // Configure API credentials
  useEffect(() => {
    if (tgUser) {
      setApiAuth(initData, {
        id: tgUser.id,
        first_name: tgUser.first_name,
        username: tgUser.username,
        role: !isTma ? devRole : undefined,
      });
    }
  }, [initData, tgUser, devRole, isTma]);

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [userData, dashData, feedData] = await Promise.all([
        api.getUserMe(),
        api.getDashboard(),
        api.getFeed(),
      ]);
      setUser(userData);
      setDashboard(dashData);
      setFeed(feedData);
    } catch (e: any) {
      console.error('Error fetching data:', e);
      setError(e.message || 'Failed to connect to coffee treasury server');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData, devRole]);

  const toggleDevRole = () => {
    if (isTma) return; // Only for browser testing preview
    const nextRole = devRole === 'admin' ? 'user' : 'admin';
    setDevRole(nextRole);
    triggerHaptic('light');
  };

  const isAdmin = user?.role === 'admin';

  return (
    <div className="min-h-screen bg-coffee-cream pb-24 text-coffee-espresso max-w-md mx-auto relative shadow-2xl overflow-x-hidden">
      {/* Header */}
      <Header
        user={user}
        onRefresh={loadData}
        isLoading={isLoading}
        onToggleDevRole={!isTma ? toggleDevRole : undefined}
      />

      <main className="px-4 pt-4 space-y-4">
        {error && (
          <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-2xl flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Tab Navigation */}
        <div className="bg-coffee-roast/5 p-1 rounded-2xl flex items-center justify-between text-xs font-bold text-coffee-latte">
          <button
            onClick={() => {
              triggerHaptic('light');
              setActiveTab('treasury');
            }}
            className={`flex-1 py-2 rounded-xl flex items-center justify-center gap-1.5 transition-all ${
              activeTab === 'treasury'
                ? 'bg-coffee-espresso text-white shadow-sm'
                : 'hover:text-coffee-espresso'
            }`}
          >
            <Coffee className="w-3.5 h-3.5" />
            <span>Pot</span>
          </button>

          <button
            onClick={() => {
              triggerHaptic('light');
              setActiveTab('spend');
            }}
            className={`flex-1 py-2 rounded-xl flex items-center justify-center gap-1.5 transition-all ${
              activeTab === 'spend'
                ? 'bg-coffee-espresso text-white shadow-sm'
                : 'hover:text-coffee-espresso'
            }`}
          >
            <PieChart className="w-3.5 h-3.5" />
            <span>Spend</span>
          </button>

          <button
            onClick={() => {
              triggerHaptic('light');
              setActiveTab('audit');
            }}
            className={`flex-1 py-2 rounded-xl flex items-center justify-center gap-1.5 transition-all ${
              activeTab === 'audit'
                ? 'bg-coffee-espresso text-white shadow-sm'
                : 'hover:text-coffee-espresso'
            }`}
          >
            <History className="w-3.5 h-3.5" />
            <span>Audit</span>
          </button>

          {isAdmin && (
            <button
              onClick={() => {
                triggerHaptic('light');
                setActiveTab('admin');
              }}
              className={`flex-1 py-2 rounded-xl flex items-center justify-center gap-1.5 transition-all ${
                activeTab === 'admin'
                  ? 'bg-amber-600 text-white shadow-sm'
                  : 'text-amber-800 hover:text-amber-900 font-extrabold'
              }`}
            >
              <Shield className="w-3.5 h-3.5" />
              <span>Admin</span>
            </button>
          )}
        </div>

        {/* Tab 1: Treasury & Main Actions */}
        {activeTab === 'treasury' && (
          <div className="space-y-4">
            <TargetProgress data={dashboard} />

            <QuickActions
              onOpenContribute={() => setIsContributeModalOpen(true)}
              paypalUrl={dashboard?.paypal_me_url || 'https://paypal.me'}
              openLink={openLink}
              triggerHaptic={triggerHaptic}
            />

            <PledgeCard
              user={user}
              onPledgeUpdated={(updated) => {
                setUser(updated);
                loadData();
              }}
              triggerHaptic={triggerHaptic}
            />
          </div>
        )}

        {/* Tab 2: Category Breakdown */}
        {activeTab === 'spend' && (
          <div className="space-y-4">
            <CategoryBreakdown data={dashboard} />
          </div>
        )}

        {/* Tab 3: Transparency Audit Feed */}
        {activeTab === 'audit' && (
          <div className="space-y-4">
            <TransparencyFeed items={feed} openLink={openLink} />
          </div>
        )}

        {/* Tab 4: Admin Controls */}
        {activeTab === 'admin' && isAdmin && (
          <div className="space-y-4">
            <AdminPanel onDataChanged={loadData} triggerHaptic={triggerHaptic} />
          </div>
        )}
      </main>

      {/* Floating Bottom Quick Contribute Button */}
      {activeTab !== 'treasury' && (
        <div className="fixed bottom-4 left-0 right-0 max-w-md mx-auto px-4 z-40">
          <button
            onClick={() => {
              triggerHaptic('medium');
              setIsContributeModalOpen(true);
            }}
            className="w-full py-3 bg-coffee-espresso hover:bg-coffee-roast active:scale-[0.98] text-white rounded-2xl font-bold text-xs flex items-center justify-center gap-2 shadow-warm-lg transition-all border border-coffee-latte/30"
          >
            <Coffee className="w-4 h-4 text-amber-400" />
            <span>Contribute to Pot</span>
          </button>
        </div>
      )}

      {/* Contribute Modal */}
      <ContributeModal
        isOpen={isContributeModalOpen}
        onClose={() => setIsContributeModalOpen(false)}
        paypalUrl={dashboard?.paypal_me_url || 'https://paypal.me'}
        onSuccess={loadData}
        triggerHaptic={triggerHaptic}
        openLink={openLink}
      />
    </div>
  );
}

export default App;
