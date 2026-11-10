import { useQuery } from "@tanstack/react-query";
import { ArrowRight, CalendarDays, Check, Search, Sprout, Trophy, TrendingUp, Users, type LucideIcon } from "lucide-react";
import { motion } from "motion/react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ChildItem } from "../components/ChildItem";
import { LineChart } from "../components/LineChart";
import { LEVEL_TONE, MiniCalendar } from "../components/MiniCalendar";
import { Button, Card, Illus, Pct, SectionHead, Segmented, Skeleton, TEST, TEST_KEYS, cx, fmtDate, fmtValue, relDays } from "../components/ui";
import { api, type EventBrief, type TestKey, type Todo } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useAct } from "../lib/hooks";

type Brief = { id: string; name: string; klass: string; gender: string; school: string; composite: number | null; text: string };
type Prog = { id: number; label: string; children: number } & Partial<Record<TestKey, number>>;
type Overview = {
  children: number; schools: number; flag_counts: Record<string, number>; lists: Record<string, Brief[]>;
  inbox: { open: number; high?: number; medium?: number; low?: number }; progress: Prog[];
  progress_by_school: Record<string, Prog[]>; school_names: Record<string, string>;
  change: Partial<Record<TestKey, { pct: number; better: boolean }>>; events: EventBrief[]; todos: Todo[];
};

function greet() {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
}

export default function Home() {
  const { user } = useAuth();
  const nav = useNavigate();
  const q = useQuery({ queryKey: ["overview"], queryFn: () => api<Overview>("/api/overview") });
  const ev = useQuery({ queryKey: ["events"], queryFn: () => api<EventBrief[]>("/api/events") });
  const [test, setTest] = useState<TestKey>("jump");
  const [ask, setAsk] = useState("");
  const done = useAct((id: number) => api(`/api/todos/${id}`, { method: "PATCH", json: { done: true } }));
  const d = q.data;

  if (!d) return <HomeSkeleton />;
  const first = user?.name.split(" ")[0] ?? "";
  const last = d.progress[d.progress.length - 1];
  const next = d.events[0];
  const best = TEST_KEYS.filter((k) => d.change[k]?.better).sort((a, b) => Math.abs(d.change[b]!.pct) - Math.abs(d.change[a]!.pct))[0];

  const tiles: { tone: string; ink: string; icon: LucideIcon; label: string; value: number; pill: string; to: string }[] = [
    { tone: "bg-lav", ink: "text-lav-ink", icon: Users, label: "Children assessed", value: d.children, pill: `${d.schools} schools · ${last?.label.split(" ")[0] ?? ""}`, to: "/children" },
    { tone: "bg-lemon", ink: "text-lemon-ink", icon: Trophy, label: "Top performers", value: d.flag_counts.top ?? 0, pill: "P85+ for their age", to: "/children?flag=top" },
    { tone: "bg-mint", ink: "text-mint-ink", icon: TrendingUp, label: "Most improved", value: d.flag_counts.improved ?? 0, pill: best ? `${TEST[best].skill} ${d.change[best]!.pct > 0 ? "+" : ""}${d.change[best]!.pct}% overall` : "since last round", to: "/children?flag=improved&sort=improved" },
    { tone: "bg-peach", ink: "text-peach-ink", icon: Sprout, label: "Need a push", value: d.flag_counts.push ?? 0, pill: `${d.flag_counts.declining ?? 0} more declining`, to: "/children?flag=push&sort=worst" },
  ];

  const ctx = Object.entries(d.progress_by_school).map(([sid, rows]) => ({
    id: sid, label: d.school_names[sid] ?? sid,
    values: d.progress.map((p) => rows.find((r) => r.id === p.id)?.[test] ?? null),
  }));
  const ch = d.change[test];

  return (
    <div className="space-y-5 md:space-y-6">
      {/* Greeting + Ask */}
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-[30px] leading-tight font-extrabold tracking-[-0.03em] md:text-[38px]">{greet()}, {first}!</h1>
          <p className="mt-1 text-[15px] text-ink-2">
            {d.inbox.open > 0 ? <><Link to="/inbox" className="font-semibold text-accent-ink hover:underline">{d.inbox.open} data checks</Link> are waiting in the Inbox.</> : "All sheets are checked."}
          </p>
        </div>
        <form onSubmit={(e) => { e.preventDefault(); nav(`/ask?q=${encodeURIComponent(ask)}`); }} className="flex h-13 w-full items-center gap-2 rounded-full bg-card pr-1.5 pl-5 shadow-card lg:w-[440px]">
          <Search className="size-[18px] shrink-0 text-ink-3" />
          <input value={ask} onChange={(e) => setAsk(e.target.value)} placeholder="Ask: fastest girls under 12…" aria-label="Ask a question"
            className="h-full min-w-0 flex-1 bg-transparent text-[15px] outline-none placeholder:text-ink-3" />
          <Button type="submit" variant="primary" size="sm" className="h-10">Ask</Button>
        </form>
      </div>

      <div className="grid gap-5 xl:grid-cols-[minmax(250px,3fr)_minmax(0,6fr)_minmax(290px,3.2fr)] xl:gap-6">
        {/* KPI tiles */}
        <div className="-mx-4 flex snap-x snap-mandatory gap-3 overflow-x-auto px-4 pb-1 no-scrollbar md:mx-0 md:grid md:grid-cols-4 md:overflow-visible md:px-0 xl:grid-cols-1 xl:content-start">
          {tiles.map((t, i) => (
            <motion.div key={t.label} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
              className="w-[72%] shrink-0 snap-start sm:w-[44%] md:w-auto">
              <Link to={t.to} className="block h-full rounded-tile bg-card p-4 shadow-card transition-transform duration-200 hover:-translate-y-0.5">
                <div className="flex items-center gap-2.5">
                  <span className={cx("grid size-9 place-items-center rounded-xl", t.tone, t.ink)}><t.icon className="size-[18px]" strokeWidth={2.2} /></span>
                  <span className="text-[13.5px] font-semibold text-ink-2">{t.label}</span>
                </div>
                <div className="num mt-3 text-[32px] leading-none font-extrabold tracking-[-0.03em]">{t.value.toLocaleString("en-IN")}</div>
                <div className="mt-2 text-[12.5px] text-ink-2">{t.pill}</div>
              </Link>
            </motion.div>
          ))}
        </div>

        {/* Centre */}
        <div className="min-w-0 space-y-5 xl:space-y-6">
          {next && <div className="md:hidden"><NextMeet e={next} /></div>}
          <Card className="p-5 md:p-6">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="text-[19px] font-bold tracking-[-0.01em]">Programme progress</h2>
                <p className="text-[13.5px] text-ink-2">Average per round. Grey lines are schools.</p>
              </div>
              {ch && (
                <span className={cx("inline-flex h-8 items-center gap-1.5 rounded-full px-3 text-[13px] font-semibold", ch.better ? "bg-mint text-mint-ink" : "bg-rose text-rose-ink")}>
                  <TrendingUp className={cx("size-4", !ch.better && "rotate-180")} />
                  {ch.pct > 0 ? "+" : ""}{ch.pct}% since {d.progress[0]?.label.split(" ")[0]}
                </span>
              )}
            </div>
            <div className="mt-4 -mx-1 overflow-x-auto no-scrollbar">
              <Segmented size="sm" value={test} onChange={setTest} options={TEST_KEYS.map((k) => ({ value: k, label: TEST[k].skill }))} />
            </div>
            <div className="mt-3">
              <LineChart xLabels={d.progress.map((p) => p.label.split(" ")[0])} main={d.progress.map((p) => p[test] ?? null)} context={ctx}
                format={(v) => fmtValue(test, v)} lowerIsBetter={test === "shuttle" || test === "relay"}
                unitNote={test === "shuttle" || test === "relay" ? "lower is faster" : "higher is better"} />
            </div>
          </Card>

          <div className="grid gap-5 lg:grid-cols-2 xl:gap-6">
            <PeopleCard title="Top performers" to="/children?flag=top" rows={d.lists.top ?? []} kind="top" />
            <PeopleCard title="Needs a push" to="/children?flag=push&sort=worst" rows={d.lists.push ?? []} kind="push" />
          </div>
        </div>

        {/* Right rail */}
        <div className="space-y-5 xl:space-y-6">
          {next && <div className="hidden md:block"><NextMeet e={next} /></div>}
          <Card className="p-5">
            <MiniCalendar events={ev.data ?? d.events} onSelect={() => nav("/calendar")} />
            <div className="mt-4 border-t border-line pt-4">
              <SectionHead title={<span className="text-[16px]">Coming up</span>} action={<Link to="/calendar" className="text-[13px] font-semibold text-ink-2 hover:text-ink">See all</Link>} className="mb-2" />
              <div className="space-y-1">
                {d.events.slice(0, 4).map((e) => (
                  <Link key={e.id} to={`/events/${e.id}`} className="flex items-center gap-3 rounded-2xl p-2 hover:bg-card-2">
                    <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-card-2 text-center leading-none">
                      <span className="num text-[16px] font-bold">{new Date(e.start_date + "T00:00").getDate()}</span>
                      <span className="text-[10px] font-semibold text-ink-3 uppercase">{fmtDate(e.start_date, { month: "short" })}</span>
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-[14px] font-semibold">{e.title}</span>
                      <span className="flex items-center gap-1.5 text-[12.5px] text-ink-2">
                        <span className="size-2 rounded-full" style={{ background: LEVEL_TONE[e.level] }} /><span className="capitalize">{e.level}</span> · {relDays(e.start_date)}
                      </span>
                    </span>
                  </Link>
                ))}
              </div>
            </div>
          </Card>
          {d.todos.length > 0 && (
            <Card className="p-5">
              <SectionHead title={<span className="text-[16px]">To do</span>} action={<Link to="/calendar" className="text-[13px] font-semibold text-ink-2 hover:text-ink">Open</Link>} className="mb-2" />
              <ul className="space-y-2">
                {d.todos.slice(0, 4).map((t) => (
                  <li key={t.id} className="flex items-start gap-2.5 text-[14px]">
                    <button onClick={() => done.mutate(t.id)} aria-label={`Mark done: ${t.text}`} className="group mt-0.5 grid size-5 shrink-0 place-items-center rounded-md border-2 border-line-2 hover:border-mint-ink">
                      <Check className="size-3.5 text-mint-ink opacity-0 group-hover:opacity-100" strokeWidth={3} />
                    </button>
                    <span className="min-w-0 flex-1">{t.text}{t.due_date && <span className="block text-[12px] text-ink-3">{relDays(t.due_date)}</span>}</span>
                  </li>
                ))}
              </ul>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

function PeopleCard({ title, to, rows, kind }: { title: string; to: string; rows: Brief[]; kind: "top" | "push" }) {
  return (
    <Card className="p-5">
      <SectionHead title={title}
        action={<Link to={to} className="flex items-center gap-1 text-[13px] font-semibold text-ink-2 hover:text-ink">All <ArrowRight className="size-3.5" /></Link>} />
      <div className="-mx-2">
        {rows.slice(0, 5).map((r) => (
          <ChildItem key={r.id} id={r.id} name={r.name} sub={`${r.school} · ${r.klass}`}
            right={<span className={cx("num rounded-full px-2.5 py-1 text-[13px] font-bold", kind === "top" ? "bg-lemon text-lemon-ink" : "bg-peach text-peach-ink")}><Pct value={r.composite} /></span>} />
        ))}
      </div>
    </Card>
  );
}

function NextMeet({ e }: { e: EventBrief }) {
  const pct = e.slots ? Math.round((e.picked / e.slots) * 100) : 0;
  return (
    <div className="overflow-hidden rounded-card bg-card shadow-card">
      <div className="bg-plate px-5 pt-4"><Illus name="track-and-field" className="mx-auto h-36 w-full object-contain object-bottom" /></div>
      <div className="p-5">
        <div className="text-[13px] font-semibold text-accent-ink">Next meet · {relDays(e.start_date)}</div>
        <div className="mt-0.5 text-[20px] leading-tight font-bold tracking-[-0.01em]">{e.title}</div>
        <div className="mt-1 flex items-center gap-1.5 text-[13px] text-ink-2"><CalendarDays className="size-3.5" />{fmtDate(e.start_date, { weekday: "short", day: "numeric", month: "short" })}{e.venue ? ` · ${e.venue.split(",")[0]}` : ""}</div>
        <div className="mt-4 mb-1.5 flex justify-between text-[12.5px] text-ink-2"><span>Athletes picked</span><span className="num font-semibold text-ink">{e.picked} / {e.slots}</span></div>
        <div className="h-2 rounded-full bg-card-2"><div className="h-full rounded-full bg-accent" style={{ width: `${Math.max(4, pct)}%` }} /></div>
        <Link to={`/events/${e.id}`} className="mt-4 inline-flex h-10 items-center gap-1.5 rounded-full bg-invert px-4 text-[14px] font-semibold text-invert-ink hover:opacity-90">
          Pick athletes <ArrowRight className="size-4" />
        </Link>
      </div>
    </div>
  );
}

function HomeSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-12 w-80" />
      <div className="grid gap-6 xl:grid-cols-[3fr_6fr_3.2fr]">
        <div className="space-y-3">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-36" />)}</div>
        <div className="space-y-6"><Skeleton className="h-96" /><Skeleton className="h-72" /></div>
        <div className="space-y-6"><Skeleton className="h-64" /><Skeleton className="h-80" /></div>
      </div>
    </div>
  );
}
