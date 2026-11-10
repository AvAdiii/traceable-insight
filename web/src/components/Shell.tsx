import { useQuery } from "@tanstack/react-query";
import { motion } from "motion/react";
import { Bell, CalendarDays, Home, LogOut, Menu, School, Settings, Sparkles, Upload, Users, type LucideIcon } from "lucide-react";
import { useState, type ReactNode } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { Avatar, IconButton, Sheet, cx } from "./ui";

type Item = { to: string; label: string; icon: LucideIcon };
const MAIN: Item[] = [
  { to: "/", label: "Home", icon: Home },
  { to: "/children", label: "Children", icon: Users },
  { to: "/schools", label: "Schools", icon: School },
  { to: "/calendar", label: "Meets", icon: CalendarDays },
  { to: "/ask", label: "Ask", icon: Sparkles },
  { to: "/upload", label: "Upload", icon: Upload },
  { to: "/settings", label: "Settings", icon: Settings },
];
const TABS: Item[] = [MAIN[0], MAIN[1], MAIN[3], MAIN[4]];

export function Logo({ className }: { className?: string }) {
  return (
    <span className={cx("text-[22px] font-extrabold tracking-[-0.04em]", className)}>
      Stride
    </span>
  );
}

function useInboxCount() {
  const q = useQuery({ queryKey: ["inbox-count"], queryFn: () => api<{ open: number }>("/api/inbox?status=open"), staleTime: 30_000 });
  return q.data?.open ?? 0;
}

export function Shell() {
  const { user, signOut } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const inbox = useInboxCount();
  const [more, setMore] = useState(false);
  const isActive = (to: string) => (to === "/" ? loc.pathname === "/" : loc.pathname.startsWith(to));

  return (
    <div className="min-h-dvh">
      {/* Desktop / tablet header with the floating pill navigation */}
      <header className="sticky top-0 z-40 hidden bg-ground px-6 pt-4 pb-3 md:block">
        <div className="mx-auto flex max-w-[1440px] items-center justify-between gap-4">
          <NavLink to="/" aria-label="Home"><Logo /></NavLink>
          <nav aria-label="Main" className="flex items-center gap-1.5 rounded-full bg-card p-1.5 shadow-card">
            {MAIN.map((it) => {
              const on = isActive(it.to);
              return (
                <NavLink key={it.to} to={it.to} aria-label={it.label} title={it.label}
                  className={cx("relative flex h-11 items-center gap-2 rounded-full px-3 text-[14px] font-semibold transition-colors", on ? "text-invert-ink" : "text-ink-2 hover:text-ink")}>
                  {on && <motion.span layoutId="pill" className="absolute inset-0 rounded-full bg-invert" transition={{ type: "spring", bounce: 0.18, duration: 0.4 }} />}
                  <it.icon className="relative size-5" strokeWidth={2} />
                  <span className={cx("relative", on ? "inline" : "hidden xl:inline")}>{it.label}</span>
                </NavLink>
              );
            })}
          </nav>
          <div className="flex items-center gap-3">
            <IconButton icon={Bell} label={`Inbox, ${inbox} data checks open`} badge={inbox} active={isActive("/inbox")} onClick={() => nav("/inbox")} />
            <AccountButton name={user?.name ?? ""} role={user?.role ?? ""} onSignOut={signOut} />
          </div>
        </div>
      </header>

      {/* Phone header */}
      <header className="sticky top-0 z-40 flex items-center justify-between bg-ground px-4 pt-[max(env(safe-area-inset-top),10px)] pb-2 md:hidden">
        <NavLink to="/" aria-label="Home"><Logo className="text-[18px]" /></NavLink>
        <div className="flex items-center gap-2">
          <IconButton icon={Bell} label={`Inbox, ${inbox} data checks open`} badge={inbox} active={isActive("/inbox")} onClick={() => nav("/inbox")} />
        </div>
      </header>

      <main className="mx-auto max-w-[1440px] px-4 pt-3 pb-36 md:px-6 md:pt-6 md:pb-16">
        <Outlet />
      </main>

      {/* Phone tab bar: floating pill */}
      <nav aria-label="Main" className="fixed inset-x-3 bottom-[max(env(safe-area-inset-bottom),12px)] z-40 md:hidden">
        <div className="mx-auto flex max-w-md items-center justify-between rounded-full bg-card p-1.5 shadow-lift">
          {TABS.map((it) => {
            const on = isActive(it.to);
            return (
              <NavLink key={it.to} to={it.to} className="relative flex h-14 flex-1 flex-col items-center justify-center gap-0.5 rounded-full">
                {on && <motion.span layoutId="tab" className="absolute inset-0 rounded-full bg-invert" transition={{ type: "spring", bounce: 0.18, duration: 0.4 }} />}
                <it.icon className={cx("relative size-[22px]", on ? "text-invert-ink" : "text-ink-2")} strokeWidth={2} />
                <span className={cx("relative text-[11px] font-semibold", on ? "text-invert-ink" : "text-ink-2")}>{it.label}</span>
              </NavLink>
            );
          })}
          <button onClick={() => setMore(true)} className="relative flex h-14 flex-1 flex-col items-center justify-center gap-0.5 rounded-full text-ink-2">
            <Menu className="size-[22px]" strokeWidth={2} />
            <span className="text-[11px] font-semibold">More</span>
          </button>
        </div>
      </nav>

      <Sheet open={more} onClose={() => setMore(false)} title="More">
        <div className="grid grid-cols-2 gap-3">
          {[
            { to: "/schools", label: "Schools", icon: School },
            { to: "/inbox", label: `Inbox · ${inbox}`, icon: Bell },
            { to: "/upload", label: "Upload sheets", icon: Upload },
            { to: "/settings", label: "Settings", icon: Settings },
          ].map((x) => (
            <button key={x.to} onClick={() => { setMore(false); nav(x.to); }} className="flex flex-col items-start gap-5 rounded-[22px] bg-card-2 p-4 text-left text-[15px] font-semibold text-ink">
              <x.icon className="size-6" strokeWidth={1.9} />
              {x.label}
            </button>
          ))}
        </div>
        <div className="mt-5 flex items-center justify-between rounded-[22px] bg-card-2 p-4">
          <div className="flex items-center gap-3">
            <Avatar name={user?.name ?? "?"} />
            <div><div className="font-semibold">{user?.name}</div><div className="text-[13px] capitalize text-ink-2">{user?.role}</div></div>
          </div>
          <button onClick={signOut} className="flex items-center gap-1.5 rounded-full px-3 py-2 text-[14px] font-semibold text-rose-ink hover:bg-rose"><LogOut className="size-4" />Sign out</button>
        </div>
      </Sheet>
    </div>
  );
}

function AccountButton({ name, role, onSignOut }: { name: string; role: string; onSignOut: () => void }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="relative">
      <button onClick={() => setOpen((o) => !o)} aria-expanded={open} aria-label="Account" className="flex items-center gap-2 rounded-full bg-card p-1 pr-3 shadow-card">
        <Avatar name={name || "?"} size={36} />
        <span className="hidden text-left leading-tight lg:block">
          <span className="block text-[13px] font-semibold">{name}</span>
          <span className="block text-[12px] capitalize text-ink-2">{role}</span>
        </span>
      </button>
      {open && (
        <>
          <button className="fixed inset-0 z-40 cursor-default" aria-label="Close menu" onClick={() => setOpen(false)} />
          <div className="absolute right-0 z-50 mt-2 w-52 rounded-2xl bg-card p-1.5 shadow-lift">
            <button onClick={onSignOut} className="flex w-full items-center gap-2 rounded-xl px-3 py-2.5 text-[14px] font-semibold text-rose-ink hover:bg-rose">
              <LogOut className="size-4" /> Sign out
            </button>
          </div>
        </>
      )}
    </div>
  );
}

export function PageTitle({ title, sub, action }: { title: ReactNode; sub?: ReactNode; action?: ReactNode }) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-4 md:mb-7">
      <div>
        <h1 className="text-[28px] leading-tight font-extrabold tracking-[-0.025em] md:text-[34px]">{title}</h1>
        {sub && <p className="mt-0.5 text-[15px] text-ink-2">{sub}</p>}
      </div>
      {action}
    </div>
  );
}
