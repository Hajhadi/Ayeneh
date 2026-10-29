'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Brain, ChevronRight, CircleUserRound, LayoutDashboard, MessageCircle, PanelLeftClose, Settings2, Sparkles, X } from 'lucide-react';
import { cn } from '@/lib/utils';

const navigation = [
  { name: 'Chat', href: '/chat', icon: MessageCircle, group: 'Reflect' },
  { name: 'Overview', href: '/cog', icon: LayoutDashboard, group: 'Reflect' },
  { name: 'Memories', href: '/memories', icon: Brain, group: 'Understand' },
  { name: 'Patterns', href: '/patterns', icon: Sparkles, group: 'Understand' },
  { name: 'Reflections', href: '/reflections', icon: Sparkles, group: 'Understand' },
  { name: 'Blind Spots', href: '/blind-spots', icon: CircleUserRound, group: 'Understand' },
  { name: 'Library', href: '/library', icon: LayoutDashboard, group: 'Explore' },
  { name: 'Diagnostics', href: '/diagnostics', icon: Settings2, group: 'System' },
  { name: 'Settings', href: '/settings', icon: Settings2, group: 'System' },
];

interface SidebarProps { open?: boolean; onClose?: () => void }

export function Sidebar({ open = false, onClose }: SidebarProps) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <>
      <AnimatePresence>{open && <motion.button aria-label="Close navigation" className="mobile-nav-backdrop" onClick={onClose} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} />}</AnimatePresence>
      <motion.aside animate={{ width: collapsed ? 76 : 256 }} transition={{ duration: 0.22, ease: 'easeOut' }} className={cn('app-sidebar', open && 'app-sidebar-open')}>
        <div className="flex h-20 items-center justify-between px-4">
          <Link href="/" className="flex items-center gap-3" onClick={onClose}><span className="brand-mark"><span /></span>{!collapsed && <span className="text-[15px] font-semibold tracking-tight text-white">Ayeneh</span>}</Link>
          <button className="sidebar-icon-button desktop-only" onClick={() => setCollapsed((value) => !value)} aria-label="Toggle navigation"><PanelLeftClose size={16} className={cn('transition-transform', collapsed && 'rotate-180')} /></button>
          <button className="sidebar-icon-button mobile-only" onClick={onClose} aria-label="Close navigation"><X size={18} /></button>
        </div>
        <nav className="flex-1 overflow-y-auto px-3 pb-4">
          {['Reflect', 'Understand', 'Explore', 'System'].map((group) => {
            const items = navigation.filter((item) => item.group === group);
            return <div key={group} className="mb-5">{!collapsed && <p className="nav-section-label">{group}</p>}{items.map((item) => { const active = pathname === item.href; const Icon = item.icon; return <Link key={item.href} href={item.href} onClick={onClose} title={collapsed ? item.name : undefined} className={cn('nav-item', active && 'nav-item-active', collapsed && 'nav-item-collapsed')}><Icon size={17} strokeWidth={active ? 2.3 : 1.8} />{!collapsed && <><span>{item.name}</span>{active && <ChevronRight size={14} className="ml-auto opacity-60" />}</>}</Link>; })}</div>;
          })}
        </nav>
        {!collapsed && <div className="mx-3 mb-4 rounded-2xl border border-violet-400/10 bg-violet-400/[0.06] p-3"><div className="mb-2 flex items-center gap-2 text-[11px] font-medium text-violet-200"><Sparkles size={13} /> Your mirror is learning</div><p className="text-[11px] leading-relaxed text-white/40">Meaningful patterns become clearer over time.</p></div>}
      </motion.aside>
    </>
  );
}
