import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ArrowUpRight, CalendarDays, Check, Clock, Download, Dumbbell, HeartPulse, MapPin, Pencil, Plus, Rabbit, Repeat, ShieldAlert, Sparkles, Trash2, Trophy, Users, Wand2, Zap, type LucideIcon } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Choice, EventForm, Input } from "../components/EventForm";
import { LEVEL_TONE } from "../components/MiniCalendar";
import { CellLink } from "../components/Receipt";
import { Todos } from "../components/Todos";
import { Avatar, Button, Illus, Card, Chip, Empty, SectionHead, Sheet, Skeleton, cx, daysUntil, fmtDate, relDays, useToast } from "../components/ui";
import { api, getToken, type Candidate, type EventDetail, type EventItem, type Suggestion } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useAct, useMeta } from "../lib/hooks";

const DISC_ICON: Record<string, LucideIcon> = { sprint: Zap, long_jump: Rabbit, throw: Dumbbell, endurance: HeartPulse, relay: Repeat, all_round: Trophy };
const DiscIcon = ({ k, className }: { k: string; className?: string }) => { const I = DISC_ICON[k] ?? Zap; return <I className={className} strokeWidth={1.9} />; };

function band(it: { gender: string; age_min: number | null; age_max: number | null }) {
  const g = it.gender === "Any" ? "Boys & girls" : it.gender;
  const a = it.age_min != null && it.age_max != null ? `age ${it.age_min}–${it.age_max}` : it.age_max != null ? `under ${it.age_max + 1}` : it.age_min != null ? `age ${it.age_min}+` : "all ages";
  return `${g}, ${a}`;
}

export default function EventPage() {
  const { id } = useParams();
  const nav = useNavigate();
  const toast = useToast();
  const { user } = useAuth();
  const canPlan = user?.role !== "trainer";
  const q = useQuery({ queryKey: ["event", id], queryFn: () => api<EventDetail>(`/api/events/${id}`) });
  const [shortlist, setShortlist] = useState<EventItem | null>(null);
  const [adding, setAdding] = useState(false);
  const [editing, setEditing] = useState(false);
  const del = useAct(() => api(`/api/events/${id}`, { method: "DELETE" }), () => { toast({ text: "Event deleted" }); nav("/calendar"); });
  const save = useAct((v: Record<string, unknown>) => api(`/api/events/${id}`, { method: "PATCH", json: v }), () => setEditing(false));
  const delItem = useAct((iid: number) => api(`/api/items/${iid}`, { method: "DELETE" }));

  if (q.isLoading) return <div className="space-y-5"><Skeleton className="h-52" /><Skeleton className="h-80" /></div>;
  if (!q.data) return <Empty art="calendar" title="Event not found" />;
  const e = q.data;
  const past = daysUntil(e.end_date ?? e.start_date) < 0;
  const pct = e.slots ? Math.round((e.picked / e.slots) * 100) : 0;

  const download = async () => {
    const r = await fetch(`/api/events/${e.id}/export.csv`, { headers: { Authorization: `Bearer ${getToken()}` } });
    const url = URL.createObjectURL(await r.blob());
    Object.assign(document.createElement("a"), { href: url, download: `${e.title.replace(/\s+/g, "_")}.csv` }).click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-5 md:space-y-6">
      <Link to="/calendar" className="flex items-center gap-1.5 text-[14px] font-semibold text-ink-2 hover:text-ink"><ArrowLeft className="size-4" />Calendar</Link>

      <div className="grid overflow-hidden rounded-card bg-[#14161c] text-white shadow-card md:grid-cols-[1fr_300px] dark:bg-[#232733]">
        <div className="order-2 p-6 md:order-1 md:p-8">
          <span className="inline-flex items-center gap-2 rounded-full bg-white/12 px-3 py-1 text-[12.5px] font-semibold capitalize">
            <span className="size-2 rounded-full" style={{ background: LEVEL_TONE[e.level] }} />{e.level} {e.kind} · {relDays(e.start_date)}
          </span>
          <h1 className="mt-3 text-[30px] leading-tight font-extrabold tracking-[-0.03em] md:text-[40px]">{e.title}</h1>
          <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[14px] text-white/80">
            <span className="flex items-center gap-1.5"><CalendarDays className="size-4" />{fmtDate(e.start_date, { weekday: "short", day: "numeric", month: "long" })}{e.end_date ? ` – ${fmtDate(e.end_date, { day: "numeric", month: "long" })}` : ""}</span>
            {e.start_time && <span className="flex items-center gap-1.5"><Clock className="size-4" />{e.start_time}</span>}
            {e.venue && <span className="flex items-center gap-1.5"><MapPin className="size-4" />{e.venue}</span>}
          </div>
          {e.notes && <p className="mt-3 text-[14px] text-white/75">{e.notes}</p>}
          {e.items > 0 && (
            <div className="mt-5 max-w-sm">
              <div className="mb-1.5 flex justify-between text-[12.5px] text-white/80"><span>Athletes picked</span><span className="num font-semibold text-white">{e.picked} / {e.slots}</span></div>
              <div className="h-2 rounded-full bg-white/15"><div className="h-full rounded-full bg-[#f2753a] transition-[width]" style={{ width: `${Math.max(3, pct)}%` }} /></div>
            </div>
          )}
          <div className="mt-5 flex flex-wrap gap-2">
            {canPlan && <button onClick={() => setAdding(true)} className="inline-flex h-10 items-center gap-1.5 rounded-full bg-white px-4 text-[14px] font-semibold text-[#14161c] hover:bg-white/90"><Plus className="size-4" />Add race</button>}
            <button onClick={download} className="inline-flex h-10 items-center gap-1.5 rounded-full bg-white/12 px-4 text-[14px] font-semibold hover:bg-white/20"><Download className="size-4" />Team list</button>
            {canPlan && <button onClick={() => setEditing(true)} className="inline-flex h-10 items-center gap-1.5 rounded-full bg-white/12 px-4 text-[14px] font-semibold hover:bg-white/20"><Pencil className="size-4" />Edit</button>}
          </div>
        </div>
        <div className="order-1 flex items-end justify-center bg-plate px-6 pt-5 md:order-2"><Illus name={e.kind === "trial" ? "runner-start" : past ? "winners" : "finish-line"} className="h-36 w-full object-contain object-bottom md:h-52" /></div>
      </div>

      <div className="grid gap-5 lg:grid-cols-[1.7fr_1fr] md:gap-6">
        <div className="space-y-4">
          {e.items_detail.length === 0 && (
            <Card><Empty art="selecting-team" title="No races yet" action={canPlan && <Button variant="primary" icon={Plus} onClick={() => setAdding(true)}>Add a race or field event</Button>}>
              Add each race with its age band and number of places.
            </Empty></Card>
          )}
          {e.items_detail.map((it) => {
            const sel = it.selections.filter((s) => s.status === "selected");
            const res = it.selections.filter((s) => s.status === "reserve");
            return (
              <Card key={it.id} className="p-5">
                <div className="flex items-start gap-3">
                  <span className="grid size-12 shrink-0 place-items-center rounded-2xl bg-card-2 text-ink-2"><DiscIcon k={it.discipline} className="size-6" /></span>
                  <div className="min-w-0 flex-1">
                    <h3 className="text-[17px] font-bold tracking-[-0.01em]">{it.name}</h3>
                    <p className="text-[13.5px] text-ink-2">{band(it)} · {it.slots} places + {it.reserves} reserves</p>
                  </div>
                  <span className={cx("num rounded-full px-2.5 py-1 text-[13px] font-bold", sel.length >= it.slots ? "bg-mint text-mint-ink" : "bg-card-2 text-ink-2")}>
                    {sel.length >= it.slots && <Check className="mr-1 inline size-3.5" strokeWidth={3} />}{sel.length}/{it.slots}
                  </span>
                </div>
                {sel.length > 0 && (
                  <ul className="mt-4 grid gap-2 sm:grid-cols-2">
                    {sel.map((s) => (
                      <li key={s.child_id}>
                        <Link to={`/children/${s.child_id}`} className="flex items-center gap-2.5 rounded-2xl bg-card-2 p-2.5 hover:bg-line">
                          <Avatar name={s.name} size={34} />
                          <span className="min-w-0 flex-1"><span className="block truncate text-[14px] font-semibold">{s.name}</span><span className="block truncate text-[12px] text-ink-2">{s.summary || s.klass}</span></span>
                          {s.result?.position && <span className={cx("num grid size-8 place-items-center rounded-full text-[13px] font-extrabold", s.result.position === 1 ? "bg-lemon text-lemon-ink" : s.result.position <= 3 ? "bg-slate text-slate-ink" : "bg-card text-ink-2")}>{s.result.position}</span>}
                        </Link>
                      </li>
                    ))}
                  </ul>
                )}
                {res.length > 0 && <p className="mt-2 text-[12.5px] text-ink-2">Reserves: {res.map((r) => r.name).join(", ")}</p>}
                <div className="mt-4 flex flex-wrap gap-2">
                  <Button size="sm" variant={sel.length ? "secondary" : "primary"} icon={Sparkles} onClick={() => setShortlist(it)}>{sel.length ? "Review picks" : "Suggest athletes"}</Button>
                  {past && sel.length > 0 && canPlan && <ResultsButton item={it} />}
                  {canPlan && <Button size="sm" variant="ghost" icon={Trash2} onClick={() => delItem.mutate(it.id)} aria-label={`Remove ${it.name}`}>Remove</Button>}
                </div>
              </Card>
            );
          })}
        </div>
        <div className="space-y-5">
          <Card className="p-5">
            <SectionHead title="Checklist" />
            <Todos items={e.todo_list} eventId={e.id} />
          </Card>
          {canPlan && (
            <Button variant="ghost" icon={Trash2} className="w-full text-rose-ink hover:bg-rose" onClick={() => { if (confirm(`Delete “${e.title}” with its races, picks and to-dos?`)) del.mutate(undefined); }}>Delete event</Button>
          )}
        </div>
      </div>

      <Sheet open={!!shortlist} onClose={() => setShortlist(null)} wide title={shortlist && <span className="flex items-center gap-2"><Wand2 className="size-5 text-accent-ink" />{shortlist.name} · {band(shortlist)}</span>}>
        {shortlist && <Shortlist item={shortlist} canPlan={canPlan} />}
      </Sheet>
      <Sheet open={adding} onClose={() => setAdding(false)} title="Add a race or field event"><ItemForm eventId={e.id} onDone={() => setAdding(false)} /></Sheet>
      <Sheet open={editing} onClose={() => setEditing(false)} title="Edit event"><EventForm initial={e} onSubmit={(v) => save.mutate(v)} busy={save.isPending} /></Sheet>
    </div>
  );
}

function Shortlist({ item, canPlan }: { item: EventItem; canPlan: boolean }) {
  const toast = useToast();
  const q = useQuery({ queryKey: ["suggest", item.id], queryFn: () => api<Suggestion>(`/api/items/${item.id}/suggest`) });
  const accept = useAct(() => api(`/api/items/${item.id}/accept`, { method: "POST" }), () => toast({ text: "Picks saved. Top places selected, next ones as reserves." }));
  const pick = useAct((v: { child_id: string; status: string; summary: string }) => api(`/api/items/${item.id}/selections`, { method: "POST", json: v }));
  if (q.isLoading) return <div className="space-y-3">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-28" />)}</div>;
  const s = q.data!;
  const weights = Object.entries(s.weights).sort((a, b) => b[1] - a[1]);
  const label: Record<string, string> = { shuttle: "shuttle run", jump: "broad jump", ball: "ball throw", relay: "relay endurance" };
  return (
    <div className="space-y-5">
      <div className="rounded-[22px] bg-lav p-4 text-lav-ink">
        <p className="text-[14px] leading-snug">
          <b className="text-ink">{s.discipline.label}</b> leans on {weights.map(([k, w], i) => <span key={k}>{i ? (i === weights.length - 1 ? " and " : ", ") : ""}<b>{label[k]}</b> {Math.round(w * 100)}%</span>)}.
          {" "}{s.pool} children are eligible on the meet date. Each is ranked by percentile among children of the same gender and age; tap a value to see its cell.
        </p>
        {canPlan && <Button variant="primary" size="sm" icon={Check} className="mt-3" loading={accept.isPending} onClick={() => accept.mutate(undefined)}>Use top {item.slots} + {item.reserves} reserves</Button>}
      </div>

      <Group title={`Suggested · ${item.slots} places`} rows={s.selected} start={1} pick={canPlan ? (c, st) => pick.mutate({ child_id: c.child_id, status: st, summary: c.summary }) : undefined} />
      {s.reserves.length > 0 && <Group title="Reserves" rows={s.reserves} start={item.slots + 1} pick={canPlan ? (c, st) => pick.mutate({ child_id: c.child_id, status: st, summary: c.summary }) : undefined} />}
      {s.more.length > 0 && <Group title="Also close" rows={s.more.slice(0, 6)} start={item.slots + item.reserves + 1} pick={canPlan ? (c, st) => pick.mutate({ child_id: c.child_id, status: st, summary: c.summary }) : undefined} quiet />}

      {s.held.length > 0 && (
        <div className="rounded-[22px] bg-peach p-4 text-peach-ink">
          <div className="flex items-center gap-2 text-[14px] font-bold text-ink"><ShieldAlert className="size-4 text-peach-ink" />Held back by a data check</div>
          <p className="mt-1 text-[13px]">These children could not be ranked because their main value waits for a check. Clear it in the Inbox and they join the list.</p>
          <ul className="mt-2 space-y-1 text-[13.5px]">
            {s.held.map((h) => <li key={h.child_id}><Link to={`/children/${h.child_id}`} className="font-semibold text-ink hover:underline">{h.name}</Link> · {h.school} · {h.why}</li>)}
          </ul>
          <Link to="/inbox" className="mt-2 inline-flex items-center gap-1 text-[13px] font-bold">Open Inbox <ArrowUpRight className="size-3.5" /></Link>
        </div>
      )}
    </div>
  );
}

function Group({ title, rows, start, pick, quiet }: { title: string; rows: Candidate[]; start: number; pick?: (c: Candidate, status: string) => void; quiet?: boolean }) {
  return (
    <section>
      <h3 className="mb-2 text-[14px] font-bold text-ink-2">{title}</h3>
      <ol className="space-y-2">
        {rows.map((c, i) => (
          <li key={c.child_id} className={cx("rounded-[22px] border p-3.5 transition-colors", c.chosen === "selected" ? "border-mint-ink/40 bg-mint/50" : c.chosen === "reserve" ? "border-sky-ink/30 bg-sky/40" : "border-line", quiet && !c.chosen && "opacity-90")}>
            <div className="flex items-center gap-3">
              <span className="num w-6 text-center text-[15px] font-extrabold text-ink-3">{start + i}</span>
              <Avatar name={c.name} size={38} />
              <Link to={`/children/${c.child_id}`} className="min-w-0 flex-1">
                <span className="block truncate text-[15px] font-semibold hover:underline">{c.name}</span>
                <span className="block truncate text-[12.5px] text-ink-2">{c.school} · {c.klass} · {c.age ? `${Math.floor(c.age)} y on meet day` : ""}</span>
              </Link>
              <span className="num rounded-full bg-invert px-2.5 py-1 text-[13px] font-bold text-invert-ink" title="Weighted percentile for this event">{Math.round(c.score)}</span>
            </div>
            <div className="mt-2.5 flex flex-wrap gap-x-4 gap-y-1.5 pl-9 text-[13px] text-ink-2">
              {c.reasons.map((r) => (
                <span key={r.field}>
                  {r.label} <CellLink cite={r.cite} label={`${r.label}, ${c.round}`} className="font-semibold text-ink">{r.text}</CellLink>
                  <span className="ml-1 text-ink-3">P{Math.round(r.percentile)}</span>
                </span>
              ))}
              {c.trend != null && Math.abs(c.trend) >= 5 && <span className={cx("font-semibold", c.trend > 0 ? "text-mint-ink" : "text-rose-ink")}>{c.trend > 0 ? "↑" : "↓"} {Math.abs(Math.round(c.trend))} pts since last round</span>}
              {c.also && <Chip className="h-6" tone="sky">Also in {c.also.join(", ")}</Chip>}
            </div>
            {pick && (
              <div className="mt-2.5 flex gap-1.5 pl-9">
                {(["selected", "reserve"] as const).map((st) => (
                  <button key={st} onClick={() => pick(c, c.chosen === st ? "none" : st)} aria-pressed={c.chosen === st}
                    className={cx("h-8 rounded-full px-3 text-[12.5px] font-semibold transition-colors", c.chosen === st ? "bg-invert text-invert-ink" : "bg-card-2 text-ink-2 hover:text-ink")}>
                    {c.chosen === st && <Check className="mr-1 inline size-3.5" strokeWidth={3} />}{st === "selected" ? "Select" : "Reserve"}
                  </button>
                ))}
              </div>
            )}
          </li>
        ))}
      </ol>
    </section>
  );
}

function ItemForm({ eventId, onDone }: { eventId: number; onDone: () => void }) {
  const meta = useMeta();
  const [v, setV] = useState({ name: "", discipline: "sprint", gender: "Girls", age_min: "", age_max: "", slots: "3", reserves: "2" });
  const set = (p: Partial<typeof v>) => setV((x) => ({ ...x, ...p }));
  const add = useAct((body: Record<string, unknown>) => api(`/api/events/${eventId}/items`, { method: "POST", json: body }), onDone);
  const disc = meta.data?.disciplines ?? [];
  return (
    <form className="space-y-4" onSubmit={(e) => {
      e.preventDefault();
      add.mutate({ ...v, age_min: v.age_min ? +v.age_min : null, age_max: v.age_max ? +v.age_max : null, slots: +v.slots, reserves: +v.reserves, name: v.name || disc.find((d) => d.key === v.discipline)?.label });
    }}>
      <div>
        <span className="mb-1 block text-[12.5px] font-semibold text-ink-2">Discipline</span>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {disc.map((d) => (
            <button type="button" key={d.key} onClick={() => set({ discipline: d.key })} aria-pressed={v.discipline === d.key}
              className={cx("flex flex-col items-start gap-1 rounded-2xl p-3 text-left transition-colors", v.discipline === d.key ? "bg-invert text-invert-ink" : "bg-card-2 hover:bg-line")}>
              <DiscIcon k={d.key} className="size-6" />
              <span className="text-[14px] font-semibold">{d.label}</span>
              <span className={cx("text-[11.5px]", v.discipline === d.key ? "opacity-75" : "text-ink-3")}>{d.examples}</span>
            </button>
          ))}
        </div>
      </div>
      <Input label="Race name" value={v.name} onChange={(e) => set({ name: e.target.value })} placeholder="e.g. 100 m sprint" />
      <Choice label="Who" value={v.gender} onChange={(g) => set({ gender: g })} options={[{ value: "Girls", label: "Girls" }, { value: "Boys", label: "Boys" }, { value: "Any", label: "Both" }]} />
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Input label="Age from" type="number" min={4} max={18} value={v.age_min} onChange={(e) => set({ age_min: e.target.value })} />
        <Input label="Age up to" type="number" min={4} max={18} value={v.age_max} onChange={(e) => set({ age_max: e.target.value })} />
        <Input label="Places" type="number" min={1} max={50} required value={v.slots} onChange={(e) => set({ slots: e.target.value })} />
        <Input label="Reserves" type="number" min={0} max={20} value={v.reserves} onChange={(e) => set({ reserves: e.target.value })} />
      </div>
      <p className="text-[12.5px] text-ink-3"><Users className="mr-1 inline size-3.5" />Age is counted on the meet date. “Under 12” means age up to 11.</p>
      <Button type="submit" variant="primary" className="w-full" loading={add.isPending}>Add race</Button>
    </form>
  );
}

function ResultsButton({ item }: { item: EventItem }) {
  const [open, setOpen] = useState(false);
  const sel = item.selections.filter((s) => s.status === "selected");
  const [rows, setRows] = useState(() => Object.fromEntries(sel.map((s) => [s.child_id, { position: s.result?.position?.toString() ?? "", mark: s.result?.mark ?? "" }])));
  const save = useAct(async () => {
    for (const s of sel) {
      const r = rows[s.child_id];
      if (r.position || r.mark) {
        const pos = r.position ? +r.position : null;
        await api(`/api/items/${item.id}/results`, { method: "POST", json: { child_id: s.child_id, position: pos, mark: r.mark, note: pos === 1 ? "Gold" : pos === 2 ? "Silver" : pos === 3 ? "Bronze" : "" } });
      }
    }
  }, () => setOpen(false));
  return (
    <>
      <Button size="sm" icon={Pencil} onClick={() => setOpen(true)}>Results</Button>
      <Sheet open={open} onClose={() => setOpen(false)} title={`Results · ${item.name}`}>
        <p className="mb-4 text-[14px] text-ink-2">Positions become achievements on each child’s profile.</p>
        <ul className="space-y-2">
          {sel.map((s) => (
            <li key={s.child_id} className="flex items-center gap-3 rounded-2xl bg-card-2 p-2.5">
              <Avatar name={s.name} size={34} />
              <span className="min-w-0 flex-1 truncate text-[14px] font-semibold">{s.name}</span>
              <input aria-label={`Position for ${s.name}`} inputMode="numeric" placeholder="Pos." value={rows[s.child_id].position} onChange={(e) => setRows((x) => ({ ...x, [s.child_id]: { ...x[s.child_id], position: e.target.value } }))} className="num h-10 w-16 rounded-xl bg-card px-3 text-center outline-none focus:ring-2 focus:ring-accent/50" />
              <input aria-label={`Mark for ${s.name}`} placeholder="Time / distance" value={rows[s.child_id].mark} onChange={(e) => setRows((x) => ({ ...x, [s.child_id]: { ...x[s.child_id], mark: e.target.value } }))} className="h-10 w-32 rounded-xl bg-card px-3 outline-none focus:ring-2 focus:ring-accent/50" />
            </li>
          ))}
        </ul>
        <Button variant="primary" className="mt-5 w-full" loading={save.isPending} onClick={() => save.mutate(undefined)}>Save results</Button>
      </Sheet>
    </>
  );
}
