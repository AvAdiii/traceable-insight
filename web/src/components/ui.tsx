import { clsx } from "clsx";
import { AnimatePresence, motion } from "motion/react";
import {
  CircleDashed, HeartPulse, Dumbbell, Rabbit, Sprout, TrendingDown, TrendingUp, Trophy, X, Zap,
  type LucideIcon,
} from "lucide-react";
import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import type { FlagKind, TestKey } from "../lib/api";

export const cx = clsx;

// ---------------------------------------------------------------- meaning maps

export const FLAG: Record<FlagKind, { label: string; icon: LucideIcon; tone: Tone }> = {
  top: { label: "Top performer", icon: Trophy, tone: "lemon" },
  improved: { label: "Most improved", icon: TrendingUp, tone: "mint" },
  push: { label: "Needs a push", icon: Sprout, tone: "peach" },
  declining: { label: "Declining", icon: TrendingDown, tone: "rose" },
  missing: { label: "Missing test", icon: CircleDashed, tone: "slate" },
};

export const TEST: Record<TestKey, { label: string; skill: string; icon: LucideIcon; tone: Tone }> = {
  jump: { label: "Broad jump", skill: "Jump", icon: Rabbit, tone: "lav" },
  shuttle: { label: "Shuttle run", skill: "Run", icon: Zap, tone: "sky" },
  ball: { label: "Ball throw", skill: "Throw", icon: Dumbbell, tone: "peach" },
  relay: { label: "Relay endurance", skill: "Endurance", icon: HeartPulse, tone: "mint" },
};
export const TEST_KEYS: TestKey[] = ["jump", "shuttle", "ball", "relay"];

export type Tone = "lav" | "sky" | "mint" | "peach" | "lemon" | "rose" | "slate";
export const TONE: Record<Tone, string> = {
  lav: "bg-lav text-lav-ink",
  sky: "bg-sky text-sky-ink",
  mint: "bg-mint text-mint-ink",
  peach: "bg-peach text-peach-ink",
  lemon: "bg-lemon text-lemon-ink",
  rose: "bg-rose text-rose-ink",
  slate: "bg-slate text-slate-ink",
};

// ---------------------------------------------------------------- atoms

export function Card({ className, children, as = "section", ...rest }: { className?: string; children: ReactNode; as?: "section" | "div" | "article" } & React.HTMLAttributes<HTMLElement>) {
  const C = as;
  return <C className={cx("rounded-card bg-card shadow-card", className)} {...rest}>{children}</C>;
}

/** Flat illustration (unDraw). Always sits on a light plate so it reads in both appearances. */
export function Illus({ name, className }: { name: string; className?: string }) {
  return <img src={`/illus/${name}.svg`} alt="" draggable={false} loading="lazy" className={cx("select-none pointer-events-none", className)} />;
}

type BtnProps = React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "ghost" | "accent"; size?: "sm" | "md"; icon?: LucideIcon; loading?: boolean };
export function Button({ variant = "secondary", size = "md", icon: Icon, loading, className, children, disabled, ...rest }: BtnProps) {
  return (
    <button
      {...rest}
      disabled={disabled || loading}
      className={cx(
        "inline-flex items-center justify-center gap-2 rounded-full font-semibold transition-[transform,background,box-shadow,opacity] duration-150 active:scale-[0.97] disabled:opacity-45",
        size === "md" ? "h-11 px-5 text-[15px]" : "h-9 px-3.5 text-[13px]",
        variant === "primary" && "bg-invert text-invert-ink hover:opacity-90",
        variant === "accent" && "bg-accent text-white hover:brightness-105 [text-shadow:0_1px_0_rgb(0_0_0/0.12)]",
        variant === "secondary" && "bg-card-2 text-ink hover:bg-line",
        variant === "ghost" && "text-ink-2 hover:bg-card-2 hover:text-ink",
        className,
      )}
    >
      {loading ? <span className="size-4 animate-spin rounded-full border-2 border-current border-t-transparent" /> : Icon ? <Icon className={size === "md" ? "size-[18px]" : "size-4"} strokeWidth={2.2} /> : null}
      {children}
    </button>
  );
}

export function IconButton({ icon: Icon, label, className, badge, active, ...rest }: React.ButtonHTMLAttributes<HTMLButtonElement> & { icon: LucideIcon; label: string; badge?: number; active?: boolean }) {
  return (
    <button
      {...rest}
      aria-label={label}
      title={label}
      className={cx(
        "relative grid size-11 shrink-0 place-items-center rounded-full transition-colors duration-150",
        active ? "bg-invert text-invert-ink" : "bg-card text-ink hover:bg-card-2 shadow-card",
        className,
      )}
    >
      <Icon className="size-5" strokeWidth={2} />
      {badge ? (
        <span className="num absolute -right-0.5 -top-0.5 grid h-5 min-w-5 place-items-center rounded-full bg-accent px-1 text-[11px] font-bold text-white ring-2 ring-card">
          {badge > 99 ? "99+" : badge}
        </span>
      ) : null}
    </button>
  );
}

export function Chip({ tone = "slate", icon: Icon, children, className, title }: { tone?: Tone; icon?: LucideIcon; children: ReactNode; className?: string; title?: string }) {
  return (
    <span title={title} className={cx("inline-flex h-7 items-center gap-1.5 rounded-full px-2.5 text-[12.5px] font-semibold whitespace-nowrap", TONE[tone], className)}>
      {Icon && <Icon className="size-3.5" strokeWidth={2.4} />}
      {children}
    </span>
  );
}

export function FlagChip({ kind, compact, title }: { kind: FlagKind; compact?: boolean; title?: string }) {
  const f = FLAG[kind];
  if (compact) {
    return (
      <span title={title ?? f.label} aria-label={f.label} className={cx("grid size-7 place-items-center rounded-full", TONE[f.tone])}>
        <f.icon className="size-3.5" strokeWidth={2.4} />
      </span>
    );
  }
  return <Chip tone={f.tone} icon={f.icon} title={title}>{f.label}</Chip>;
}

const HUES = [262, 211, 150, 24, 340, 190, 45, 290];
export function Avatar({ name, size = 40, className }: { name: string; size?: number; className?: string }) {
  const parts = name.replace(/[^A-Za-z ]/g, " ").trim().split(/\s+/).filter((p) => p.length > 1);
  const ini = ((parts[0]?.[0] ?? name[0] ?? "?") + (parts[1]?.[0] ?? "")).toUpperCase();
  let h = 0;
  for (const c of name) h = (h * 31 + c.charCodeAt(0)) >>> 0;
  const hue = HUES[h % HUES.length];
  return (
    <span
      aria-hidden
      className={cx("grid shrink-0 place-items-center rounded-full font-bold", className)}
      style={{ width: size, height: size, fontSize: size * 0.36, background: `oklch(0.9 0.06 ${hue})`, color: `oklch(0.38 0.12 ${hue})` }}
    >
      {ini}
    </span>
  );
}

export function Pct({ value, className }: { value: number | null | undefined; className?: string }) {
  if (value === null || value === undefined) return <span className={cx("text-ink-3", className)}>—</span>;
  return <span className={cx("num font-semibold", className)}>P{Math.round(value)}</span>;
}

/** A horizontal percentile meter: 0–100, with the median tick. */
export function Meter({ value, tone = "ink", className }: { value: number | null | undefined; tone?: "ink" | "accent"; className?: string }) {
  return (
    <div className={cx("relative h-2 rounded-full bg-card-2", className)} role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={value ?? undefined}>
      <span className="absolute inset-y-0 left-1/2 w-px bg-line-2" />
      {value !== null && value !== undefined && (
        <motion.span
          initial={{ width: 0 }}
          animate={{ width: `${Math.max(3, value)}%` }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          className={cx("absolute inset-y-0 left-0 rounded-full", tone === "accent" ? "bg-accent" : "bg-invert")}
        />
      )}
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cx("skeleton", className)} />;
}

export function Empty({ art = "no-data", title, children, action }: { art?: string; title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center px-6 py-10 text-center">
      <span className="mb-4 rounded-[22px] bg-plate p-4"><Illus name={art} className="h-24 w-36 object-contain" /></span>
      <h3 className="text-[17px] font-semibold">{title}</h3>
      {children && <p className="mt-1 max-w-sm text-[14px] text-ink-2">{children}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function Segmented<T extends string>({ value, onChange, options, className, size = "md" }: { value: T; onChange: (v: T) => void; options: { value: T; label: ReactNode }[]; className?: string; size?: "sm" | "md" }) {
  return (
    <div role="tablist" className={cx("inline-flex rounded-full bg-card-2 p-1", className)}>
      {options.map((o) => (
        <button
          key={o.value}
          role="tab"
          aria-selected={o.value === value}
          onClick={() => onChange(o.value)}
          className={cx(
            "relative rounded-full font-semibold transition-colors",
            size === "md" ? "h-9 px-4 text-[14px]" : "h-8 px-3 text-[13px]",
            o.value === value ? "text-invert-ink" : "text-ink-2 hover:text-ink",
          )}
        >
          {o.value === value && <motion.span layoutId={`seg-${options.map((x) => x.value).join()}`} className="absolute inset-0 rounded-full bg-invert" transition={{ type: "spring", bounce: 0.15, duration: 0.35 }} />}
          <span className="relative">{o.label}</span>
        </button>
      ))}
    </div>
  );
}

export function SectionHead({ title, action, className }: { title: ReactNode; action?: ReactNode; className?: string }) {
  return (
    <div className={cx("mb-3 flex items-center justify-between gap-3", className)}>
      <h2 className="text-[19px] font-bold tracking-[-0.01em]">{title}</h2>
      {action}
    </div>
  );
}

// ---------------------------------------------------------------- sheet (bottom sheet on phone, drawer on desktop)

export function Sheet({ open, onClose, title, children, wide }: { open: boolean; onClose: () => void; title?: ReactNode; children: ReactNode; wide?: boolean }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const k = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", k);
    const prev = document.activeElement as HTMLElement | null;
    ref.current?.focus();
    document.body.style.overflow = "hidden";
    return () => { window.removeEventListener("keydown", k); document.body.style.overflow = ""; prev?.focus?.(); };
  }, [open, onClose]);
  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50">
          <motion.div className="absolute inset-0 bg-black/40" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose} />
          <motion.div
            ref={ref}
            role="dialog"
            aria-modal="true"
            tabIndex={-1}
            initial={{ y: "100%" }}
            animate={{ y: 0 }}
            exit={{ y: "100%" }}
            transition={{ type: "spring", damping: 32, stiffness: 340 }}
            drag="y"
            dragConstraints={{ top: 0, bottom: 0 }}
            dragElastic={{ top: 0, bottom: 0.6 }}
            onDragEnd={(_, i) => { if (i.offset.y > 120 || i.velocity.y > 600) onClose(); }}
            className={cx(
              "absolute inset-x-0 bottom-0 flex max-h-[92dvh] flex-col rounded-t-[30px] bg-card shadow-lift outline-none",
              "md:inset-y-3 md:right-3 md:left-auto md:max-h-none md:rounded-[30px]",
              wide ? "md:w-[min(760px,calc(100vw-24px))]" : "md:w-[480px]",
            )}
          >
            <div className="mx-auto mt-2.5 h-1.5 w-10 shrink-0 rounded-full bg-line-2 md:hidden" />
            <div className="flex items-start justify-between gap-3 px-5 pt-3 pb-2 md:px-6 md:pt-5">
              <div className="min-w-0 flex-1 text-[19px] font-bold tracking-[-0.01em]">{title}</div>
              <button onClick={onClose} aria-label="Close" className="grid size-9 shrink-0 place-items-center rounded-full bg-card-2 text-ink-2 hover:text-ink">
                <X className="size-[18px]" />
              </button>
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-5 pb-6 safe-b md:px-6" onPointerDownCapture={(e) => e.stopPropagation()}>
              {children}
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}

// ---------------------------------------------------------------- toast

type ToastMsg = { id: number; text: string; action?: { label: string; run: () => void } };
const ToastCtx = createContext<(t: Omit<ToastMsg, "id">) => void>(() => {});
export const useToast = () => useContext(ToastCtx);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastMsg[]>([]);
  const push = useCallback((t: Omit<ToastMsg, "id">) => {
    const id = Date.now() + Math.random();
    setItems((xs) => [...xs.slice(-2), { ...t, id }]);
    setTimeout(() => setItems((xs) => xs.filter((x) => x.id !== id)), 5000);
  }, []);
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="pointer-events-none fixed inset-x-0 bottom-28 z-[60] flex flex-col items-center gap-2 px-4 md:bottom-8" aria-live="polite">
        <AnimatePresence>
          {items.map((t) => (
            <motion.div key={t.id} initial={{ opacity: 0, y: 16, scale: 0.96 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 8 }}
              className="pointer-events-auto flex max-w-md items-center gap-4 rounded-full bg-invert py-2.5 pr-2.5 pl-5 text-[14px] font-medium text-invert-ink shadow-lift">
              <span>{t.text}</span>
              {t.action && (
                <button onClick={() => { t.action!.run(); setItems((xs) => xs.filter((x) => x.id !== t.id)); }} className="rounded-full bg-white/15 px-3 py-1.5 text-[13px] font-semibold hover:bg-white/25">
                  {t.action.label}
                </button>
              )}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastCtx.Provider>
  );
}

// ---------------------------------------------------------------- formatting

export const fmtDate = (iso: string, opts: Intl.DateTimeFormatOptions = { day: "numeric", month: "short" }) =>
  new Date(iso + (iso.length === 10 ? "T00:00:00" : "")).toLocaleDateString("en-IN", opts);

export function daysUntil(iso: string): number {
  const d = new Date(iso + "T00:00:00").getTime();
  const t = new Date(); t.setHours(0, 0, 0, 0);
  return Math.round((d - t.getTime()) / 86400000);
}

export function relDays(iso: string): string {
  const n = daysUntil(iso);
  if (n === 0) return "Today";
  if (n === 1) return "Tomorrow";
  if (n === -1) return "Yesterday";
  return n > 0 ? `In ${n} days` : `${-n} days ago`;
}

export function fmtValue(test: TestKey, v: number | null | undefined) {
  if (v === null || v === undefined) return "—";
  return test === "shuttle" || test === "relay" ? `${v.toFixed(1)} s` : `${v.toFixed(2)} m`;
}
