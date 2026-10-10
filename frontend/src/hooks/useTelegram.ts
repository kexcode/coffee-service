import { useEffect, useState } from 'react';
import WebApp from '@twa-dev/sdk';

export interface TelegramUser {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
}

export function useTelegram() {
  const [isReady, setIsReady] = useState(false);
  const [initData, setInitData] = useState<string>('');
  const [tgUser, setTgUser] = useState<TelegramUser | null>(null);
  const [isTma, setIsTma] = useState(false);

  useEffect(() => {
    try {
      if (typeof window !== 'undefined' && WebApp) {
        WebApp.ready();
        WebApp.expand();

        // Configure header and background colors to match artisanal theme
        try {
          WebApp.setHeaderColor('#2b1810');
          WebApp.setBackgroundColor('#fbf7ee');
        } catch {
          // ignore if unsupported in older TMA clients
        }

        const data = WebApp.initData || '';
        const user = (WebApp.initDataUnsafe as { user?: TelegramUser })?.user;

        setInitData(data);
        if (user) {
          setTgUser(user);
          setIsTma(true);
        } else {
          // Running in browser preview outside Telegram
          setIsTma(false);
          setTgUser({
            id: 999999,
            first_name: 'Coffee Enthusiast',
            username: 'espresso_lover',
          });
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
      if (WebApp && WebApp.HapticFeedback) {
        if (type === 'success' || type === 'warning' || type === 'error') {
          WebApp.HapticFeedback.notificationOccurred(type);
        } else {
          WebApp.HapticFeedback.impactOccurred(type);
        }
      }
    } catch {
      // Haptics not available in regular browsers
    }
  };

  const openLink = (url: string) => {
    try {
      if (isTma && WebApp.openLink) {
        WebApp.openLink(url);
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
