'use client';

import { createContext, useContext, useEffect, useState } from 'react';

type Theme = 'light' | 'dark' | 'system';

const ThemeContext = createContext<{
  theme: Theme;
  setTheme: (theme: Theme) => void;
}>({ theme: 'system', setTheme: () => {} });

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState<Theme>('system');

  useEffect(() => {
    const saved = window.localStorage.getItem('ayeneh_theme');
    if (saved === 'light' || saved === 'dark' || saved === 'system') setTheme(saved);
  }, []);

  function applyTheme(nextTheme: Theme) {
    setTheme(nextTheme);
    window.localStorage.setItem('ayeneh_theme', nextTheme);
  }

  useEffect(() => {
    const root = document.documentElement;
    root.classList.remove('light', 'dark');

    if (theme === 'system') {
      const media = window.matchMedia('(prefers-color-scheme: dark)');
      root.classList.add(media.matches ? 'dark' : 'light');
      const onChange = (event: MediaQueryListEvent) => {
        root.classList.remove('light', 'dark');
        root.classList.add(event.matches ? 'dark' : 'light');
      };
      media.addEventListener?.('change', onChange);
      return () => media.removeEventListener?.('change', onChange);
    } else {
      root.classList.add(theme);
    }
  }, [theme]);

  return (
    <ThemeContext.Provider value={{ theme, setTheme: applyTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export const useTheme = () => useContext(ThemeContext);
