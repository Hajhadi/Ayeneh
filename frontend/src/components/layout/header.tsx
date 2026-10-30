'use client';

import { useAuthStore } from '@/stores/auth-store';
import { Button } from '@/components/ui/button';
import { ArrowLeft, Menu, Sparkles } from 'lucide-react';
import { usePathname, useRouter } from 'next/navigation';

interface HeaderProps {
  title?: string;
  onMenuClick?: () => void;
}

export function Header({ title, onMenuClick }: HeaderProps) {
  const { user, logout } = useAuthStore();
  const pathname = usePathname();
  const router = useRouter();
  const goBack = () => {
    if (window.history.length > 1) router.back();
    else router.push('/chat');
  };

  return (
    <header className="app-header">
      <div className="flex items-center gap-3">
        <button className="mobile-only sidebar-icon-button" onClick={onMenuClick} aria-label="Open navigation"><Menu size={20} /></button>
        {pathname !== '/chat' && <button className="sidebar-icon-button" onClick={goBack} aria-label="Go back"><ArrowLeft size={18} /></button>}
        <div><p className="eyebrow"><Sparkles size={11} /> COGNITIVE MIRROR</p><h1 className="text-[15px] font-semibold text-white">{title || 'Ayeneh'}</h1></div>
      </div>
      <div className="flex items-center gap-4">
        {user && <span className="hidden text-xs text-white/40 sm:block">{user.email}</span>}
        <Button variant="ghost" size="sm" onClick={logout}><span className="hidden sm:inline">Sign out</span><span className="sm:hidden">Exit</span></Button>
      </div>
    </header>
  );
}
