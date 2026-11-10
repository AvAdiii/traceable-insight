import { ChevronLeft, ChevronRight } from "lucide-react";
import { useMemo, useState } from "react";
import type { EventBrief } from "../lib/api";
import { cx } from "./ui";

const DOW = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];
export const LEVEL_TONE: Record<string, string> = {
  school: "var(--sky-ink)", zonal: "var(--lav-ink)", district: "var(--accent)", state: "var(--rose-ink)",
  national: "var(--rose-ink)", annual: "var(--mint-ink)",
};
const iso = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

export function eventDays(e: EventBrief): string[] {
  const out: string[] = [];
  const a = new Date(e.start_date + "T00:00:00");
  const b = new Date((e.end_date ?? e.start_date) + "T00:00:00");
  for (let d = new Date(a); d <= b; d.setDate(d.getDate() + 1)) out.push(iso(d));
  return out;
}

export function MiniCalendar({ events, selected, onSelect, big }: { events: EventBrief[]; selected?: string | null; onSelect?: (day: string) => void; big?: boolean }) {
  const today = iso(new Date());
  const [cursor, setCursor] = useState(() => { const d = new Date(); d.setDate(1); return d; });
  const byDay = useMemo(() => {
    const m: Record<string, EventBrief[]> = {};
    events.forEach((e) => eventDays(e).forEach((d) => (m[d] ??= []).push(e)));
    return m;
  }, [events]);
  const first = new Date(cursor);
  const start = new Date(first); start.setDate(1 - first.getDay());
  const cells = Array.from({ length: 42 }, (_, i) => { const d = new Date(start); d.setDate(start.getDate() + i); return d; });
  const rows = cells[35].getMonth() !== cursor.getMonth() ? cells.slice(0, 35) : cells;
  const move = (n: number) => setCursor((c) => new Date(c.getFullYear(), c.getMonth() + n, 1));

  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <h3 className={cx("font-bold tracking-[-0.01em]", big ? "text-[22px]" : "text-[17px]")}>
          {cursor.toLocaleDateString("en-IN", { month: "long", year: "numeric" })}
        </h3>
        <div className="flex gap-1">
          <button aria-label="Previous month" onClick={() => move(-1)} className="grid size-9 place-items-center rounded-full text-ink-2 hover:bg-card-2 hover:text-ink"><ChevronLeft className="size-[18px]" /></button>
          <button aria-label="Next month" onClick={() => move(1)} className="grid size-9 place-items-center rounded-full text-ink-2 hover:bg-card-2 hover:text-ink"><ChevronRight className="size-[18px]" /></button>
        </div>
      </div>
      <div className="grid grid-cols-7 text-center">
        {DOW.map((d) => <div key={d} className="pb-2 text-[12px] font-semibold text-ink-3">{d}</div>)}
        {rows.map((d) => {
          const k = iso(d);
          const evs = byDay[k] ?? [];
          const inMonth = d.getMonth() === cursor.getMonth();
          const isToday = k === today;
          const isSel = k === selected;
          return (
            <button key={k} onClick={() => onSelect?.(k)} aria-label={`${d.toDateString()}${evs.length ? `, ${evs.map((e) => e.title).join(", ")}` : ""}`}
              className={cx("relative mx-auto flex flex-col items-center justify-center rounded-full", big ? "h-14 w-full max-w-14" : "size-10")}>
              <span className={cx("num grid place-items-center rounded-full text-[14px] font-semibold transition-colors",
                big ? "size-10" : "size-8",
                isToday ? "bg-accent text-white" : isSel ? "bg-invert text-invert-ink" : inMonth ? "text-ink hover:bg-card-2" : "text-ink-3/60")}>
                {d.getDate()}
              </span>
              {evs.length > 0 && (
                <span className="absolute bottom-0.5 flex gap-0.5">
                  {evs.slice(0, 3).map((e) => <span key={e.id} className="size-1.5 rounded-full" style={{ background: LEVEL_TONE[e.level] ?? "var(--ink-3)" }} />)}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
