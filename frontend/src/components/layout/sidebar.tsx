'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';

const navigation = [
  { name: 'Chat', href: '/chat', icon: '💬' },
  { name: 'Memories', href: '/memories', icon: '🧠' },
  { name: 'Patterns', href: '/patterns', icon: '🔄' },
  { name: 'Reflections', href: '/reflections', icon: '🪞' },
  { name: 'Blind Spots', href: '/blind-spots', icon: '👁️' },
  { name: 'Library', href: '/library', icon: '📚' },
  { name: 'Jobs', href: '/jobs', icon: '⚡' },
  { name: 'Diagnostics', href: '/diagnostics', icon: '🔍' },
  { name: 'Settings', href: '/settings', icon: '⚙️' },
  { name: 'Profile', href: '/profile', icon: '👤' },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-screen w-64 flex-col" style={{ borderRight: '1px solid rgba(255,255,255,0.06)', background: '#12121E' }}>
      <div className="flex h-16 items-center px-4" style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
        <span className="text-xl font-bold" style={{ color: '#fff' }}>Ayeneh</span>
      </div>
      <nav className="flex-1 space-y-1 p-4">
        {navigation.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
              pathname === item.href
                ? 'text-purple-400'
                : 'text-gray-400 hover:text-white'
            )}
            style={{
              background: pathname === item.href ? 'rgba(124,58,237,0.1)' : 'transparent',
            }}
          >
            <span>{item.icon}</span>
            <span>{item.name}</span>
          </Link>
        ))}
      </nav>
    </aside>
  );
}
