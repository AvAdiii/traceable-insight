import { Check, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { api, type Todo } from "../lib/api";
import { useAct } from "../lib/hooks";
import { cx, relDays } from "./ui";

export function Todos({ items, eventId }: { items: Todo[]; eventId?: number }) {
  const [text, setText] = useState("");
  const [due, setDue] = useState("");
  const add = useAct((v: { text: string; due_date: string | null }) => api("/api/todos", { method: "POST", json: { ...v, event_id: eventId ?? null } }), () => { setText(""); setDue(""); });
  const toggle = useAct((t: Todo) => api(`/api/todos/${t.id}`, { method: "PATCH", json: { done: !t.done } }));
  const del = useAct((t: Todo) => api(`/api/todos/${t.id}`, { method: "DELETE" }));
  return (
    <div>
      <ul className="space-y-1">
        {items.map((t) => {
          const late = !t.done && t.due_date && new Date(t.due_date + "T23:59") < new Date();
          return (
            <li key={t.id} className="group flex items-start gap-3 rounded-2xl px-2 py-2 hover:bg-card-2">
              <button onClick={() => toggle.mutate(t)} aria-label={t.done ? "Mark not done" : "Mark done"} aria-pressed={t.done}
                className={cx("mt-0.5 grid size-6 shrink-0 place-items-center rounded-lg border-2 transition-colors", t.done ? "border-mint-ink bg-mint-ink text-white" : "border-line-2 hover:border-ink-3")}>
                {t.done && <Check className="size-4" strokeWidth={3} />}
              </button>
              <span className="min-w-0 flex-1">
                <span className={cx("block text-[14.5px]", t.done && "text-ink-3 line-through")}>{t.text}</span>
                {t.due_date && <span className={cx("text-[12px]", late ? "font-semibold text-rose-ink" : "text-ink-3")}>{late ? "Overdue · " : ""}{relDays(t.due_date)}</span>}
              </span>
              <button onClick={() => del.mutate(t)} aria-label="Delete to-do" className="grid size-8 place-items-center rounded-full text-ink-3 opacity-0 transition-opacity group-hover:opacity-100 focus:opacity-100 hover:bg-rose hover:text-rose-ink">
                <Trash2 className="size-4" />
              </button>
            </li>
          );
        })}
      </ul>
      <form onSubmit={(e) => { e.preventDefault(); if (text.trim()) add.mutate({ text: text.trim(), due_date: due || null }); }} className="mt-2 flex gap-2">
        <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Add a to-do" aria-label="New to-do"
          className="h-11 min-w-0 flex-1 rounded-2xl bg-card-2 px-4 text-[14.5px] outline-none focus:ring-2 focus:ring-accent/50" />
        <input type="date" value={due} onChange={(e) => setDue(e.target.value)} aria-label="Due date" className="h-11 w-[132px] rounded-2xl bg-card-2 px-3 text-[13px] outline-none" />
        <button type="submit" aria-label="Add" className="grid size-11 shrink-0 place-items-center rounded-full bg-invert text-invert-ink"><Plus className="size-5" /></button>
      </form>
    </div>
  );
}
