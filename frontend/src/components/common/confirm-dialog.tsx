'use client';

import { ReactNode } from 'react';

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  danger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({
  open, title, message, confirmLabel = 'Confirm', cancelLabel = 'Cancel',
  danger = false, onConfirm, onCancel,
}: ConfirmDialogProps) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="rounded-lg shadow-xl max-w-md w-full mx-4 p-6" style={{ background: '#1A1A2E', border: '1px solid rgba(255,255,255,0.06)' }}>
        <h3 className="text-lg font-semibold" style={{ color: '#fff' }}>{title}</h3>
        <p className="mt-2 text-sm" style={{ color: 'rgba(255,255,255,0.5)' }}>{message}</p>
        <div className="mt-4 flex justify-end gap-3">
          <button onClick={onCancel} className="px-4 py-2 text-sm rounded-md hover:bg-white/5" style={{ border: '1px solid rgba(255,255,255,0.06)', color: 'rgba(255,255,255,0.6)' }}>
            {cancelLabel}
          </button>
          <button
            onClick={onConfirm}
            className="px-4 py-2 text-sm rounded-md text-white"
            style={{ background: danger ? '#EF4444' : '#7C3AED' }}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
