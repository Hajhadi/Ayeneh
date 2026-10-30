import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';

const native = vi.hoisted(() => ({
  listProfiles: vi.fn(), saveProfile: vi.fn(), setActiveProvider: vi.fn(), removeProfile: vi.fn(),
}));

vi.mock('@/lib/secure-model', () => ({
  SecureModel: native,
  secureModelAvailable: () => true,
}));

import { ModelProfilesSettings } from '@/components/settings/model-profiles-settings';

describe('model connections', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    native.listProfiles.mockResolvedValue({
      activeProvider: 'personal',
      profiles: [
        { provider: 'personal', service: 'openai', label: 'Personal', baseUrl: 'https://api.openai.com/v1', model: 'gpt-4o-mini', hasKey: true },
        { provider: 'gemini-work', service: 'gemini', label: 'Gemini work', baseUrl: 'https://generativelanguage.googleapis.com/v1beta', model: 'gemini-3.8-flash', hasKey: true },
      ],
    });
    native.saveProfile.mockResolvedValue(undefined);
    native.setActiveProvider.mockResolvedValue(undefined);
  });

  it('shows independent saved keys and lets the user activate Gemini', async () => {
    render(<ModelProfilesSettings />);
    expect(await screen.findByText('Personal')).toBeInTheDocument();
    expect(screen.getByText('Gemini work')).toBeInTheDocument();
    fireEvent.click(screen.getByText('Use'));
    await waitFor(() => expect(native.setActiveProvider).toHaveBeenCalledWith({ provider: 'gemini-work' }));
  });

  it('adds another named Gemini key without replacing existing profiles', async () => {
    render(<ModelProfilesSettings />);
    await screen.findByText('Personal');
    fireEvent.click(screen.getByText('Add another'));
    fireEvent.change(screen.getByLabelText('Name (to distinguish your keys)'), { target: { value: 'Backup Gemini' } });
    fireEvent.change(screen.getByLabelText('Service'), { target: { value: 'gemini' } });
    fireEvent.change(screen.getByLabelText('API key'), { target: { value: 'dummy-test-key' } });
    fireEvent.click(screen.getByText('Save connection'));
    await waitFor(() => expect(native.saveProfile).toHaveBeenCalledWith(expect.objectContaining({
      provider: expect.stringMatching(/^p_/), service: 'gemini', label: 'Backup Gemini',
      apiKey: 'dummy-test-key',
    })));
    expect(screen.getByText('Personal')).toBeInTheDocument();
    expect(screen.getByText('Gemini work')).toBeInTheDocument();
  });
});
