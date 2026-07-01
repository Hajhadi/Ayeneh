'use client';

import { useAuthStore } from '@/stores/auth-store';
import { Button } from '@/components/ui/button';

interface HeaderProps {
  title?: string;
}

export function Header({ title }: HeaderProps) {
  const { user, logout } = useAuthStore();

  return (
    <header className="flex h-16 items-center justify-between px-6" style={{ borderBottom: '1px solid rgba(255,255,255,0.06)', background: 'rgba(22,22,30,0.8)' }}>
      <h1 className="text-lg font-semibold" style={{ color: '#fff' }}>{title || 'Ayeneh'}</h1>
      <div className="flex items-center gap-4">
        {user && <span className="text-sm" style={{ color: 'rgba(255,255,255,0.5)' }}>{user.email}</span>}
        <Button variant="ghost" size="sm" onClick={logout}>
          Sign out
        </Button>
      </div>
    </header>
  );
}
