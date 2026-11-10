import { useQuery } from "@tanstack/react-query";
import { CalendarPlus, MapPin, Trophy } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { EventForm } from "../components/EventForm";
import { LEVEL_TONE, MiniCalendar, eventDays } from "../components/MiniCalendar";
import { PageTitle } from "../components/Shell";
import { Todos } from "../components/Todos";
import { Button, Card, Empty, SectionHead, Segmented, Sheet, cx, daysUntil, fmtDate, relDays } from "../components/ui";
import { api, type EventBrief, type EventDetail, type Todo } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useAct } from "../lib/hooks";

export default function Calendar() {
  const nav = useNavigate();
  const { user } = useAuth();
  const canPlan = user?.role !== "trainer";
  const ev = useQuery({ queryKey: ["events"], queryFn: () => api<EventBrief[]>("/api/events") });
  const todos = useQuery({ queryKey: ["todos"], queryFn: () => api<Todo[]>("/api/todos") });
  const [day, setDay] = useState<string | null>(null);
  const [when, setWhen] = useState<"upcoming" | "past">("upcoming");
  const [creating, setCreating] = useState(false);
  const create = useAct((v: Record<string, unknown>) => api<EventDetail>("/api/events", { method: "POST", json: v }), (r) => { setCreating(false); nav(`/events/${r.id}`); });
  const all = ev.data ?? [];
  let list = day ? all.filter((e) => eventDays(e).includes(day)) : all.filter((e) => (when === "upcoming" ? daysUntil(e.end_date ?? e.start_date) >= 0 : daysUntil(e.end_date ?? e.start_date) < 0));
  if (when === "past" && !day) list = [...list].reverse();

  return (
    <div>
      <PageTitle title="Meets"
        action={canPlan && <Button variant="primary" icon={CalendarPlus} onClick={() => setCreating(true)}>New event</Button>} />
      <div className="grid gap-5 lg:grid-cols-[1.25fr_1fr] md:gap-6">
        <div className="space-y-5 md:space-y-6">
          <Card className="p-5 md:p-6"><MiniCalendar big events={all} selected={day} onSelect={(d) => setDay((x) => (x === d ? null : d))} /></Card>
          <Card className="p-5 md:p-6">
            <SectionHead title={<span className="flex items-center gap-2">Checklist</span>} />
            <Todos items={todos.data ?? []} />
          </Card>
        </div>
        <Card className="p-5 md:p-6">
          <SectionHead title={day ? fmtDate(day, { weekday: "long", day: "numeric", month: "long" }) : "Events"}
            action={day ? <Button size="sm" onClick={() => setDay(null)}>All dates</Button> : <Segmented size="sm" value={when} onChange={setWhen} options={[{ value: "upcoming", label: "Upcoming" }, { value: "past", label: "Past" }]} />} />
          {list.length === 0 && <Empty art="calendar" title={day ? "Nothing on this day" : "No events here"} action={canPlan && <Button onClick={() => setCreating(true)} icon={CalendarPlus}>Add one</Button>} />}
          <ul className="space-y-3">
            {list.map((e) => <EventRow key={e.id} e={e} />)}
          </ul>
        </Card>
      </div>
      <Sheet open={creating} onClose={() => setCreating(false)} title="New event">
        <EventForm onSubmit={(v) => create.mutate(v)} busy={create.isPending} submitLabel="Create and add races" initial={day ? { start_date: day } : undefined} />
      </Sheet>
    </div>
  );
}

export function EventRow({ e }: { e: EventBrief }) {
  const pct = e.slots ? e.picked / e.slots : 0;
  const n = daysUntil(e.start_date);
  return (
    <li>
      <Link to={`/events/${e.id}`} className="flex gap-4 rounded-[22px] bg-card-2 p-4 transition-colors hover:bg-line">
        <span className="grid size-14 shrink-0 place-items-center rounded-2xl bg-card text-center leading-none shadow-card">
          <span><span className="num block text-[20px] font-extrabold">{new Date(e.start_date + "T00:00").getDate()}</span><span className="text-[11px] font-bold text-ink-3 uppercase">{fmtDate(e.start_date, { month: "short" })}</span></span>
        </span>
        <span className="min-w-0 flex-1">
          <span className="flex items-center gap-2 text-[12.5px] font-semibold text-ink-2">
            <span className="size-2 rounded-full" style={{ background: LEVEL_TONE[e.level] }} /><span className="capitalize">{e.level} {e.kind}</span>
            <span className={cx(n >= 0 && n <= 14 && "text-accent-ink")}>· {relDays(e.start_date)}</span>
          </span>
          <span className="mt-0.5 block text-[16px] font-bold tracking-[-0.01em]">{e.title}</span>
          {e.venue && <span className="mt-0.5 flex items-center gap-1 truncate text-[13px] text-ink-2"><MapPin className="size-3.5 shrink-0" />{e.venue}</span>}
          {e.items > 0 && (
            <span className="mt-2.5 flex items-center gap-2 text-[12.5px] text-ink-2">
              <Trophy className="size-3.5" />{e.items} races · <span className="num">{e.picked}/{e.slots}</span> picked
              <span className="h-1.5 w-20 rounded-full bg-card"><span className="block h-full rounded-full bg-accent" style={{ width: `${Math.max(4, pct * 100)}%` }} /></span>
            </span>
          )}
        </span>
      </Link>
    </li>
  );
}
