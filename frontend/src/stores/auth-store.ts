import { create } from 'zustand';
import { authClient, User } from '@/lib/auth-client';

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  setUser: (user: User | null) => void;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, displayName: string) => Promise<void>;
  logout: () => Promise<void>;
  checkAuth: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,

  setUser: (user) => set({ user, isAuthenticated: !!user }),

  login: async (email, password) => {
    await authClient.login(email, password);
    set({ isAuthenticated: true });
  },

  register: async (email, password, displayName) => {
    await authClient.register(email, password, displayName);
    set({ isAuthenticated: true });
  },

  logout: async () => {
    await authClient.logout();
    set({ user: null, isAuthenticated: false });
  },

  checkAuth: async () => {
    if (!authClient.isAuthenticated()) {
      set({ isLoading: false });
      return;
    }
    try {
      const user = await fetch('/api/v1/users/me', {
        headers: { Authorization: `Bearer ${authClient.getAccessTokenValue()}` },
      }).then((r) => r.json());
      set({ user, isAuthenticated: true, isLoading: false });
    } catch {
      set({ isLoading: false });
    }
  },
}));
