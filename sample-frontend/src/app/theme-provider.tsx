import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";
import { ThemeContext, type Theme, type ThemeContextValue } from "./theme-context";

interface ThemeProviderProps {
  children: ReactNode;
  defaultTheme?: Theme;
  storageKey?: string;
}

export function ThemeProvider({
  children,
  defaultTheme = "light",
  storageKey = "app-theme",
}: ThemeProviderProps) {
  const [theme, setThemeState] = useState<Theme>(defaultTheme);

  useEffect(() => {
    const stored = window.localStorage.getItem(storageKey) as Theme | null;
    if (stored === "light" || stored === "dark") {
      setThemeState(stored);
    }
  }, [storageKey]);

  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle("dark", theme === "dark");
    window.localStorage.setItem(storageKey, theme);
  }, [theme, storageKey]);

  const setTheme = (next: Theme) => setThemeState(next);
  const toggleTheme = () => setThemeState((t) => (t === "light" ? "dark" : "light"));

  const value = useMemo<ThemeContextValue>(() => ({ theme, setTheme, toggleTheme }), [theme]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}


