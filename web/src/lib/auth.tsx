import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api, getToken, setToken, type User } from "./api";

type AuthCtx = { user: User | null; signIn: (email: string, password: string) => Promise<void>; signOut: () => void };
const Ctx = createContext<AuthCtx>({ user: null, signIn: async () => {}, signOut: () => {} });
export const useAuth = () => useContext(Ctx);
const USER_KEY = "ti.user";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(() => {
    try { return getToken() ? JSON.parse(localStorage.getItem(USER_KEY) || "null") : null; } catch { return null; }
  });
  useEffect(() => {
    const out = () => setUser(null);
    window.addEventListener("ti:signed-out", out);
    return () => window.removeEventListener("ti:signed-out", out);
  }, []);
  const signIn = async (email: string, password: string) => {
    const r = await api<{ token: string; user: User }>("/api/auth/login", { method: "POST", json: { email, password } });
    setToken(r.token);
    try { localStorage.setItem(USER_KEY, JSON.stringify(r.user)); } catch { /* ignore */ }
    setUser(r.user);
  };
  const signOut = () => { setToken(null); try { localStorage.removeItem(USER_KEY); } catch { /* ignore */ } setUser(null); };
  return <Ctx.Provider value={{ user, signIn, signOut }}>{children}</Ctx.Provider>;
}
