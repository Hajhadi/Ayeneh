'use client';

import { useState } from 'react';
import { useTheme } from '@/providers/theme-provider';
import { PageLayout } from '@/components/layout/page-layout';
import { Button } from '@/components/ui/button';

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();

  return (
    <PageLayout title="Settings" description="Configure your Ayeneh experience">
      <div className="max-w-2xl space-y-6">
        <div className="rounded-lg p-6" style={{ border: '1px solid rgba(255,255,255,0.06)', background: '#1A1A2E' }}>
          <h3 className="text-lg font-medium mb-4" style={{ color: '#fff' }}>Appearance</h3>
          <div className="space-y-3">
            <label className="block text-sm font-medium" style={{ color: 'rgba(255,255,255,0.5)' }}>Theme</label>
            <div className="flex gap-2">
              {(['light', 'dark', 'system'] as const).map((t) => (
                <Button
                  key={t}
                  variant={theme === t ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setTheme(t)}
                >
                  {t.charAt(0).toUpperCase() + t.slice(1)}
                </Button>
              ))}
            </div>
          </div>
        </div>

        <div className="rounded-lg p-6" style={{ border: '1px solid rgba(255,255,255,0.06)', background: '#1A1A2E' }}>
          <h3 className="text-lg font-medium mb-4" style={{ color: '#fff' }}>Notifications</h3>
          <p className="text-sm" style={{ color: 'rgba(255,255,255,0.4)' }}>Configure notification preferences for reflections, pattern updates, and blind spot alerts.</p>
          <div className="mt-3 space-y-2">
            {['Reflections ready', 'New patterns detected', 'Blind spots identified'].map((item) => (
              <label key={item} className="flex items-center gap-2 text-sm" style={{ color: 'rgba(255,255,255,0.6)' }}>
                <input type="checkbox" defaultChecked className="rounded" />
                {item}
              </label>
            ))}
          </div>
        </div>

        <div className="rounded-lg p-6" style={{ border: '1px solid rgba(255,255,255,0.06)', background: '#1A1A2E' }}>
          <h3 className="text-lg font-medium mb-4" style={{ color: '#fff' }}>Data & Privacy</h3>
          <p className="text-sm mb-3" style={{ color: 'rgba(255,255,255,0.4)' }}>Manage your data retention and privacy settings.</p>
          <div className="flex gap-2">
            <Button variant="outline" size="sm">Export Data</Button>
            <Button variant="destructive" size="sm">Delete Account</Button>
          </div>
        </div>

        <div className="rounded-lg p-6" style={{ border: '1px solid rgba(255,255,255,0.06)', background: '#1A1A2E' }}>
          <h3 className="text-lg font-medium mb-4" style={{ color: '#fff' }}>About</h3>
          <div className="text-sm space-y-1" style={{ color: 'rgba(255,255,255,0.4)' }}>
            <p>Ayeneh — Cognitive Companion</p>
            <p>Version 0.1.0</p>
          </div>
        </div>
      </div>
    </PageLayout>
  );
}
