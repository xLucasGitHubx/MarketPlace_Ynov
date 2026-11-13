import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { clearStoredToken, getStoredToken, setStoredToken } from "@/api/client";

interface AuthContextValue {
  token: string;
  setToken: (value: string) => void;
  clearToken: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState(() => getStoredToken());

  const setToken = useCallback((value: string) => {
    setStoredToken(value);
    setTokenState(value.trim());
  }, []);

  const clearToken = useCallback(() => {
    clearStoredToken();
    setTokenState("");
  }, []);

  const value = useMemo(
    () => ({
      token,
      setToken,
      clearToken,
      isAuthenticated: token.length > 0,
    }),
    [token, setToken, clearToken],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
