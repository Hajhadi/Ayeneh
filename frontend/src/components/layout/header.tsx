'use client';

import { useAuthStore } from '@/stores/auth-store';
import { Button } from '@/components/ui/button';
import { Menu, Sparkles } from 'lucide-react';

interface HeaderProps {
  title?: string;
  onMenuClick?: () => void;
}

export function Header({ title, onMenuClick }: HeaderProps) {
  const { user, logout } = useAuthStore();

  return (
    <header className="app-header">
      <div className="flex items-center gap-3">
        <button className="mobile-only sidebar-icon-button" onClick={onMenuClick} aria-label="Open navigation"><Menu size={20} /></button>
        <div><p className="eyebrow"><Sparkles size={11} /> COGNITIVE MIRROR</p><h1 className="text-[15px] font-semibold text-white">{title || 'Ayeneh'}</h1></div>
      </div>
      <div className="flex items-center gap-4">
        {user && <span className="hidden text-xs text-white/40 sm:block">{user.email}</span>}
        <Button variant="ghost" size="sm" onClick={logout}><span className="hidden sm:inline">Sign out</span><span className="sm:hidden">Exit</span></Button>
      </div>
    </header>
  );
}
