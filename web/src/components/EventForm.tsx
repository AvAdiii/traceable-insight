import { useState } from "react";
import type { EventBrief } from "../lib/api";
import { Button, cx } from "./ui";

export const KINDS = ["meet", "trial", "assessment", "session", "other"];
export const LEVELS = ["school", "zonal", "district", "state", "national", "annual"];

export function Input({ label, className, ...rest }: { label: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className={cx("block", className)}>
      <span className="mb-1 block text-[12.5px] font-semibold text-ink-2">{label}</span>
      <input {...rest} className="h-11 w-full rounded-2xl bg-card-2 px-4 text-[15px] font-medium outline-none focus:ring-2 focus:ring-accent/50" />
    </label>
  );
}

export function Choice({ label, value, onChange, options }: { label: string; value: string; onChange: (v: string) => void; options: { value: string; label: string }[] }) {
  return (
    <div>
      <span className="mb-1 block text-[12.5px] font-semibold text-ink-2">{label}</span>
      <div className="flex flex-wrap gap-1.5">
        {options.map((o) => (
          <button type="button" key={o.value} onClick={() => onChange(o.value)} aria-pressed={value === o.value}
            className={cx("h-9 rounded-full px-3.5 text-[13.5px] font-semibold capitalize transition-colors", value === o.value ? "bg-invert text-invert-ink" : "bg-card-2 text-ink-2 hover:text-ink")}>
            {o.label}
          </button>
        ))}
      </div>
    </div>
  );
}

export function EventForm({ initial, onSubmit, busy, submitLabel = "Save" }: { initial?: Partial<EventBrief>; onSubmit: (v: Record<string, unknown>) => void; busy?: boolean; submitLabel?: string }) {
  const [v, setV] = useState({
    title: initial?.title ?? "", kind: initial?.kind ?? "meet", level: initial?.level ?? "district",
    start_date: initial?.start_date ?? new Date().toISOString().slice(0, 10), end_date: initial?.end_date ?? "",
    start_time: initial?.start_time ?? "08:00", venue: initial?.venue ?? "", notes: initial?.notes ?? "",
  });
  const set = (p: Partial<typeof v>) => setV((x) => ({ ...x, ...p }));
  return (
    <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); onSubmit({ ...v, end_date: v.end_date || null }); }}>
      <Input label="Name" required value={v.title} onChange={(e) => set({ title: e.target.value })} placeholder="e.g. Inter-school athletics meet" />
      <Choice label="Type" value={v.kind} onChange={(x) => set({ kind: x })} options={KINDS.map((k) => ({ value: k, label: k }))} />
      <Choice label="Level" value={v.level} onChange={(x) => set({ level: x })} options={LEVELS.map((k) => ({ value: k, label: k }))} />
      <div className="grid grid-cols-2 gap-3">
        <Input label="Starts" type="date" required value={v.start_date} onChange={(e) => set({ start_date: e.target.value })} />
        <Input label="Ends (optional)" type="date" value={v.end_date ?? ""} min={v.start_date} onChange={(e) => set({ end_date: e.target.value })} />
        <Input label="Time" type="time" value={v.start_time} onChange={(e) => set({ start_time: e.target.value })} />
        <Input label="Venue" value={v.venue} onChange={(e) => set({ venue: e.target.value })} placeholder="Stadium or school" />
      </div>
      <label className="block">
        <span className="mb-1 block text-[12.5px] font-semibold text-ink-2">Notes</span>
        <textarea value={v.notes} onChange={(e) => set({ notes: e.target.value })} rows={3} className="w-full rounded-2xl bg-card-2 px-4 py-3 text-[15px] outline-none focus:ring-2 focus:ring-accent/50" />
      </label>
      <Button type="submit" variant="primary" loading={busy} className="w-full">{submitLabel}</Button>
    </form>
  );
}
