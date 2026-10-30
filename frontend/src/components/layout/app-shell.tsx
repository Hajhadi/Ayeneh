'use client';

import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Sidebar } from './sidebar';
import { Header } from './header';

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [navigationOpen, setNavigationOpen] = useState(false);
  const isLanding = pathname === '/';
  const isChat = pathname === '/chat';

  useEffect(() => {
    const onAndroidBack = () => {
      if (navigationOpen) {
        setNavigationOpen(false);
        return;
      }
      if (window.history.length > 1) window.history.back();
      else window.location.href = '/';
    };
    window.addEventListener('ayeneh:android-back', onAndroidBack);
    return () => window.removeEventListener('ayeneh:android-back', onAndroidBack);
  }, [navigationOpen]);

  if (isLanding || isChat) return <>{children}</>;

  return <div className="app-frame">
    <Sidebar open={navigationOpen} onClose={() => setNavigationOpen(false)} />
    <motion.main className="app-main" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.25 }}>
      <Header onMenuClick={() => setNavigationOpen(true)} />
      {children}
    </motion.main>
    <AnimatePresence>{navigationOpen && <div className="mobile-nav-spacer" />}</AnimatePresence>
  </div>;
}
