'use client';

import { useState } from 'react';
import { useUser, useUpdateProfile, useUserStats } from '@/hooks/use-api';
import { PageLayout } from '@/components/layout/page-layout';
import { Skeleton } from '@/components/common/skeleton';
import { Button } from '@/components/ui/button';

export default function ProfilePage() {
  const { data: user, isLoading } = useUser();
  const { data: stats } = useUserStats();
  const updateMutation = useUpdateProfile();
  const [name, setName] = useState('');

  if (isLoading) return <PageLayout title="Profile"><Skeleton className="h-40" /></PageLayout>;

  return (
    <PageLayout title="Profile" description="Your account information">
      <div className="max-w-2xl space-y-6">
        <div className="rounded-lg p-6" style={{ border: '1px solid rgba(255,255,255,0.06)', background: '#1A1A2E' }}>
          <h3 className="text-lg font-medium mb-4" style={{ color: '#fff' }}>Account Information</h3>
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium mb-1" style={{ color: 'rgba(255,255,255,0.5)' }}>Email</label>
              <p className="text-sm" style={{ color: '#fff' }}>{user?.email}</p>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1" style={{ color: 'rgba(255,255,255,0.5)' }}>Role</label>
              <p className="text-sm" style={{ color: '#fff' }}>{user?.role}</p>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1" style={{ color: 'rgba(255,255,255,0.5)' }}>Display Name</label>
              <div className="flex gap-2">
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder={user?.display_name || 'Set display name'}
                  className="flex-1 rounded-md px-3 py-2 text-sm"
                  style={{ border: '1px solid rgba(255,255,255,0.06)', background: 'transparent', color: '#fff' }}
                />
                <Button
                  size="sm"
                  onClick={() => { if (name.trim()) updateMutation.mutate({ display_name: name }); }}
                  disabled={!name.trim() || updateMutation.isPending}
                >
                  {updateMutation.isPending ? 'Saving...' : 'Save'}
                </Button>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1" style={{ color: 'rgba(255,255,255,0.5)' }}>Member Since</label>
              <p className="text-sm" style={{ color: '#fff' }}>{user?.created_at ? new Date(user.created_at).toLocaleDateString() : 'Unknown'}</p>
            </div>
          </div>
        </div>

        {stats && (
          <div className="rounded-lg p-6" style={{ border: '1px solid rgba(255,255,255,0.06)', background: '#1A1A2E' }}>
            <h3 className="text-lg font-medium mb-4" style={{ color: '#fff' }}>Usage Statistics</h3>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
              {Object.entries(stats as Record<string, unknown>).map(([key, value]) => (
                <div key={key} className="rounded-lg p-3" style={{ background: 'rgba(255,255,255,0.03)' }}>
                  <div className="text-xs capitalize" style={{ color: 'rgba(255,255,255,0.4)' }}>{key.replace(/_/g, ' ')}</div>
                  <div className="text-lg font-semibold" style={{ color: '#fff' }}>{typeof value === 'number' ? value.toLocaleString() : String(value)}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </PageLayout>
  );
}
