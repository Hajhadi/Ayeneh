import { api, ApiError } from './api-client';

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface User {
  id: string;
  email: string;
  role: string;
  display_name?: string;
}

class AuthClient {
  private storage = typeof window !== 'undefined' ? localStorage : null;

  private getAccessToken(): string | null {
    return this.storage?.getItem('access_token') ?? null;
  }

  private getRefreshToken(): string | null {
    return this.storage?.getItem('refresh_token') ?? null;
  }

  private setTokens(tokens: TokenPair) {
    this.storage?.setItem('access_token', tokens.access_token);
    this.storage?.setItem('refresh_token', tokens.refresh_token);
  }

  private clearTokens() {
    this.storage?.removeItem('access_token');
    this.storage?.removeItem('refresh_token');
  }

  async register(email: string, password: string, displayName: string): Promise<TokenPair> {
    const tokens = await api.post<TokenPair>('/api/v1/auth/register', {
      email,
      password,
      display_name: displayName,
    });
    this.setTokens(tokens);
    return tokens;
  }

  async login(email: string, password: string): Promise<TokenPair> {
    const tokens = await api.post<TokenPair>('/api/v1/auth/login', {
      email,
      password,
    });
    this.setTokens(tokens);
    return tokens;
  }

  async logout(): Promise<void> {
    try {
      await api.post('/api/v1/auth/logout');
    } finally {
      this.clearTokens();
    }
  }

  async refresh(): Promise<TokenPair> {
    const refreshToken = this.getRefreshToken();
    if (!refreshToken) throw new Error('No refresh token');

    const tokens = await api.post<TokenPair>('/api/v1/auth/refresh', {
      refresh_token: refreshToken,
    });
    this.setTokens(tokens);
    return tokens;
  }

  isAuthenticated(): boolean {
    return !!this.getAccessToken();
  }

  getAccessTokenValue(): string | null {
    return this.getAccessToken();
  }
}

export const authClient = new AuthClient();
