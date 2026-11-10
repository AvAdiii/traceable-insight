import { SlidersHorizontal, X } from "lucide-react";
import { useState } from "react";
import type { Meta } from "../lib/api";
import { Button, FLAG, Sheet, TEST, TEST_KEYS, cx } from "./ui";

export type Filters = { q?: string; school?: string; klass?: string; gender?: string; age_min?: string; age_max?: string; flag?: string; test?: string; sort?: string; round_id?: string; coach?: string };
const CLASSES = ["Class I", "Class II", "Class III", "Class IV", "Class V", "Class VI", "Class VII", "Class VIII", "Class IX", "Class X"];

function Select({ label, value, onChange, options }: { label: string; value?: string; onChange: (v: string) => void; options: { value: string; label: string }[] }) {
  return (
    <label className="block">
      <span className="mb-1 block text-[12.5px] font-semibold text-ink-2">{label}</span>
      <select value={value ?? ""} onChange={(e) => onChange(e.target.value)}
        className="h-11 w-full appearance-none rounded-2xl bg-card-2 bg-[length:16px] bg-[right_14px_center] bg-no-repeat px-4 pr-10 text-[15px] font-medium outline-none focus:ring-2 focus:ring-accent/50"
        style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23888' stroke-width='2.5'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E\")" }}>
        <option value="">Any</option>
        {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </label>
  );
}

export function FilterFields({ f, set, meta }: { f: Filters; set: (p: Partial<Filters>) => void; meta?: Meta }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <Select label="School" value={f.school} onChange={(v) => set({ school: v })} options={(meta?.schools ?? []).map((s) => ({ value: s.id, label: s.short }))} />
      <Select label="Coach (PT trainer)" value={f.coach} onChange={(v) => set({ coach: v })} options={(meta?.coaches ?? []).filter((c) => c.role === "trainer").map((c) => ({ value: String(c.id), label: c.name }))} />
      <Select label="Class" value={f.klass} onChange={(v) => set({ klass: v })} options={CLASSES.map((c) => ({ value: c, label: c }))} />
      <Select label="Gender" value={f.gender} onChange={(v) => set({ gender: v })} options={[{ value: "Girls", label: "Girls" }, { value: "Boys", label: "Boys" }]} />
      <Select label="Age from" value={f.age_min} onChange={(v) => set({ age_min: v })} options={Array.from({ length: 12 }, (_, i) => ({ value: String(i + 5), label: `${i + 5} years` }))} />
      <Select label="Age up to" value={f.age_max} onChange={(v) => set({ age_max: v })} options={Array.from({ length: 12 }, (_, i) => ({ value: String(i + 5), label: `${i + 5} years` }))} />
      <Select label="Round" value={f.round_id} onChange={(v) => set({ round_id: v })} options={(meta?.rounds ?? []).map((r) => ({ value: String(r.id), label: r.label }))} />
      <Select label="Rank by" value={f.test} onChange={(v) => set({ test: v })} options={TEST_KEYS.map((k) => ({ value: k, label: TEST[k].label }))} />
    </div>
  );
}

export function FlagRow({ value, onChange }: { value?: string; onChange: (v?: string) => void }) {
  const kinds = Object.keys(FLAG) as (keyof typeof FLAG)[];
  return (
    <div className="-mx-4 flex gap-2 overflow-x-auto px-4 no-scrollbar md:mx-0 md:flex-wrap md:px-0">
      <button onClick={() => onChange(undefined)} className={cx("h-9 shrink-0 rounded-full px-4 text-[13.5px] font-semibold transition-colors", !value ? "bg-invert text-invert-ink" : "bg-card text-ink-2 shadow-card hover:text-ink")}>Everyone</button>
      {kinds.map((k) => {
        const F = FLAG[k];
        const on = value === k;
        return (
          <button key={k} onClick={() => onChange(on ? undefined : k)} aria-pressed={on}
            className={cx("flex h-9 shrink-0 items-center gap-1.5 rounded-full px-3.5 text-[13.5px] font-semibold transition-colors", on ? "bg-invert text-invert-ink" : "bg-card text-ink-2 shadow-card hover:text-ink")}>
            <F.icon className="size-4" strokeWidth={2.3} />{F.label}
          </button>
        );
      })}
    </div>
  );
}

export function FilterButton({ f, set, meta, count }: { f: Filters; set: (p: Partial<Filters>) => void; meta?: Meta; count: number }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button icon={SlidersHorizontal} onClick={() => setOpen(true)} className="bg-card shadow-card">
        Filters{count ? <span className="num grid size-5 place-items-center rounded-full bg-accent text-[11px] text-white">{count}</span> : null}
      </Button>
      <Sheet open={open} onClose={() => setOpen(false)} title="Filters">
        <FilterFields f={f} set={set} meta={meta} />
        <div className="mt-6 flex gap-2">
          <Button icon={X} onClick={() => set({ school: "", klass: "", gender: "", age_min: "", age_max: "", round_id: "", test: "", coach: "" })}>Clear</Button>
          <Button variant="primary" className="flex-1" onClick={() => setOpen(false)}>Show children</Button>
        </div>
      </Sheet>
    </>
  );
}
