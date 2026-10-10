import { useEffect, useState } from 'react';
import WebApp from '@twa-dev/sdk';

export interface TelegramUser {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
}

function getTelegramContext() {
  if (typeof window === 'undefined') {
    return { initData: '', user: null as TelegramUser | null, isTma: false };
  }

  // Check WebApp from sdk or window
  const twa = (window as any).Telegram?.WebApp || WebApp;
  let initData = twa?.initData || '';

  // Fallback: check location hash or search if twa hasn't parsed it yet
  if (!initData && window.location.hash.includes('tgWebAppData=')) {
    const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ''));
    initData = hashParams.get('tgWebAppData') || '';
  }
  if (!initData && window.location.search.includes('tgWebAppData=')) {
    const searchParams = new URLSearchParams(window.location.search);
    initData = searchParams.get('tgWebAppData') || '';
  }

  const user = (twa?.initDataUnsafe as { user?: TelegramUser })?.user || null;
  const isTma = Boolean(initData || user);

  return { initData, user, isTma };
}

export function useTelegram() {
  const initial = getTelegramContext();
  const [initData, setInitData] = useState<string>(initial.initData);
  const [tgUser, setTgUser] = useState<TelegramUser | null>(initial.user);
  const [isTma, setIsTma] = useState<boolean>(initial.isTma);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    try {
      if (typeof window !== 'undefined') {
        const twa = (window as any).Telegram?.WebApp || WebApp;
        if (twa) {
          try {
            twa.ready();
            twa.expand();
            twa.setHeaderColor('#2b1810');
            twa.setBackgroundColor('#fbf7ee');
          } catch {
            // ignore older client versions
          }

          const ctx = getTelegramContext();
          if (ctx.initData) setInitData(ctx.initData);
          if (ctx.user) {
            setTgUser(ctx.user);
            setIsTma(true);
          } else if (!ctx.isTma) {
            // Browser preview outside Telegram
            setIsTma(false);
            setTgUser({
              id: 999999,
              first_name: 'Coffee Enthusiast',
              username: 'espresso_lover',
            });
          }
        }
      }
    } catch (e) {
      console.warn('Telegram WebApp initialization error:', e);
    } finally {
      setIsReady(true);
    }
  }, []);

  const triggerHaptic = (type: 'light' | 'medium' | 'heavy' | 'success' | 'warning' | 'error' = 'light') => {
    try {
      const twa = (window as any).Telegram?.WebApp || WebApp;
      if (twa?.HapticFeedback) {
        if (type === 'success' || type === 'warning' || type === 'error') {
          twa.HapticFeedback.notificationOccurred(type);
        } else {
          twa.HapticFeedback.impactOccurred(type);
        }
      }
    } catch {
      // Haptics not available in regular browsers
    }
  };

  const openLink = (url: string) => {
    try {
      const twa = (window as any).Telegram?.WebApp || WebApp;
      if (isTma && twa?.openLink) {
        twa.openLink(url);
      } else {
        window.open(url, '_blank', 'noopener,noreferrer');
      }
    } catch {
      window.open(url, '_blank', 'noopener,noreferrer');
    }
  };

  return {
    isReady,
    initData,
    tgUser,
    isTma,
    triggerHaptic,
    openLink,
    WebApp,
  };
}
