import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowRight, ArrowUp, Cpu, Laptop, ListFilter, Sparkles } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { CellLink } from "../components/Receipt";
import { PageTitle } from "../components/Shell";
import { Avatar, Card, Illus, Chip, FlagChip, Pct, Skeleton, TEST, cx, fmtValue } from "../components/ui";
import { api, type Candidate, type ChildDetail, type ChildRow, type TestKey } from "../lib/api";
import { getState, ollamaAvailable, ollamaModelName, subscribe, type EngineState } from "../lib/llm";
import { route } from "../lib/llm";
import type { SchoolSummary } from "./Schools";

type CompareCell = { value: number | null; raw: string; unit: string; status: string; note: string; percentile: number | null; cite: ChildRow["cite"] } | null;
type CompareSide = { query: string; matches: ChildRow[]; child: { id: string; name: string; gender: string; klass: string; school: string; age: number | null; round: string | null; composite: number | null } | null };
type CompareRow = { field: TestKey; label: string; unit: string; lower_is_better: boolean; asked: boolean; cells: CompareCell[]; winner: number | null };

type Answer = {
  kind: "children" | "shortlist" | "schools" | "count" | "child" | "compare" | "empty"; title: string; sentence: string; chips: string[]; routed_by: string; question: string;
  spec: Record<string, unknown>; rows: unknown[]; test?: TestKey; count?: number; by_school?: Record<string, number>;
  child?: ChildDetail; fact?: { field: TestKey; cite: ChildRow["cite"]; raw: string; unit: string } | null; held?: { child_id: string; name: string; why: string }[]; reserves?: Candidate[];
  sides?: CompareSide[]; table?: CompareRow[];
};

export function useEngine() {
  const [s, setS] = useState<EngineState>(getState());
  useEffect(() => subscribe(setS), []);
  return s;
}

export default function Ask() {
  const [sp, setSp] = useSearchParams();
  const [text, setText] = useState("");
  const [thread, setThread] = useState<Answer[]>([]);
  const engine = useEngine();
  const [laptop, setLaptop] = useState(false);
  useEffect(() => { void ollamaAvailable().then(setLaptop); }, []);
  const prompt = useQuery({ queryKey: ["ask-prompt"], queryFn: () => api<{ suggested: string[] }>("/api/ask/prompt") });
  const end = useRef<HTMLDivElement>(null);
  const ask = useMutation({
    mutationFn: async (input: string | { spec: Record<string, unknown>; question: string; routed_by: string }) => {
      if (typeof input !== "string")  // a pick from an earlier answer: the spec is already settled
        return api<Answer>("/api/ask/run", { method: "POST", json: { spec: input.spec, question: "", routed_by: input.routed_by } })
          .then((a) => ({ ...a, question: input.question }));
      const r = await route(input);
      return api<Answer>("/api/ask/run", { method: "POST", json: { spec: r.spec, question: input, routed_by: r.routed_by } });
    },
    onSuccess: (a) => { setThread((t) => [...t, a]); if (a.routed_by.startsWith("Laptop")) setLaptop(true); },
  });
  const send = (q: string) => { if (!q.trim() || ask.isPending) return; setText(""); ask.mutate(q.trim()); };
  const asked = useRef(false);
  useEffect(() => {
    const q = sp.get("q");
    if (q && !asked.current) { asked.current = true; send(q); setSp({}, { replace: true }); }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [thread.length, ask.isPending]);

  return (
    <div className="mx-auto max-w-3xl">
      <PageTitle title="Ask" action={<EngineBadge s={engine} laptop={laptop} />} />

      {thread.length === 0 && !ask.isPending && (
        <Card className="p-6">
          <div className="mb-5 rounded-[22px] bg-plate p-4"><Illus name="questions" className="mx-auto h-32 w-full object-contain" /></div>
          <h2 className="relative text-[17px] font-bold">Try one of these</h2>
          <div className="relative mt-3 flex flex-wrap gap-2">
            {(prompt.data?.suggested ?? []).map((s) => (
              <button key={s} onClick={() => send(s)} className="rounded-full bg-card-2 px-4 py-2.5 text-left text-[14px] font-medium hover:bg-line">{s}</button>
            ))}
          </div>
          <p className="relative mt-5 text-[13px] text-ink-2">The model only reads your question, never children’s data.</p>
        </Card>
      )}

      <div className="space-y-6">
        <AnimatePresence initial={false}>
          {thread.map((a, i) => (
            <motion.div key={i} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }} className="space-y-3">
              <div className="flex justify-end"><div className="max-w-[85%] rounded-[22px] rounded-br-md bg-invert px-4 py-2.5 text-[15px] text-invert-ink">{a.question}</div></div>
              <AnswerCard a={a} onPick={(side, id, name) => {
                const names = [...((a.spec.names as string[]) ?? [])];
                names[side] = id;
                const label = (a.sides ?? []).map((x, j) => (j === side ? name : x.child?.name ?? x.query)).join(" vs ");
                if (!ask.isPending) ask.mutate({ spec: { ...a.spec, names }, question: label, routed_by: a.routed_by });
              }} />
            </motion.div>
          ))}
        </AnimatePresence>
        {ask.isPending && <div className="space-y-2"><Skeleton className="ml-auto h-11 w-2/3" /><Skeleton className="h-48" /></div>}
        {ask.isError && <p className="rounded-2xl bg-rose p-4 text-[14px] text-rose-ink">Could not answer that: {(ask.error as Error).message}</p>}
        <div ref={end} />
      </div>

      <form onSubmit={(e) => { e.preventDefault(); send(text); }}
        className="sticky bottom-28 z-30 mt-6 flex items-center gap-2 rounded-full bg-card p-1.5 pl-5 shadow-lift md:bottom-6">
        <Sparkles className="size-[18px] shrink-0 text-accent" />
        <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Who are the best throwers in Class VII?" aria-label="Your question"
          className="h-11 min-w-0 flex-1 bg-transparent text-[16px] outline-none placeholder:text-ink-3" />
        <button type="submit" disabled={!text.trim() || ask.isPending} aria-label="Ask" className="grid size-11 shrink-0 place-items-center rounded-full bg-invert text-invert-ink transition-opacity disabled:opacity-30">
          <ArrowUp className="size-5" strokeWidth={2.5} />
        </button>
      </form>
    </div>
  );
}

export function EngineBadge({ s, laptop }: { s: EngineState; laptop?: boolean }) {
  const [label, tone, Icon] =
    s.status !== "ready" && s.status !== "loading" && laptop ? [`Laptop model · ${ollamaModelName()}`, "bg-mint text-mint-ink", Laptop] as const
    : s.status === "ready" ? ["On-device model ready", "bg-mint text-mint-ink", Cpu] as const
      : s.status === "loading" ? [`Loading model ${Math.round(s.progress * 100)}%`, "bg-sky text-sky-ink", Cpu] as const
        : s.status === "unsupported" ? ["Rules mode", "bg-slate text-slate-ink", ListFilter] as const
          : ["Rules mode · get the model in Settings", "bg-slate text-slate-ink", Laptop] as const;
  return <Link to="/settings#ai"><Chip tone="slate" className={tone}><Icon className="size-3.5" />{label}</Chip></Link>;
}

function AnswerCard({ a, onPick }: { a: Answer; onPick: (side: number, id: string, name: string) => void }) {
  const childLink = a.kind === "children" ? `/children?${new URLSearchParams(Object.entries({ school: a.spec.school, gender: a.spec.gender, klass: a.spec.klass, age_min: a.spec.age_min, age_max: a.spec.age_max, flag: a.spec.flag, test: a.spec.test, sort: a.spec.sort }).filter(([, v]) => v != null && v !== "").map(([k, v]) => [k, String(v)]))}` : null;
  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-center gap-1.5">
        {a.chips.map((c) => <Chip key={c} tone="lav">{c}</Chip>)}
        <span className="ml-auto text-[11.5px] font-semibold text-ink-3">Understood by: {a.routed_by}</span>
      </div>
      <h3 className="mt-3 text-[20px] font-bold tracking-[-0.01em]">{a.title}</h3>
      <p className="mt-0.5 text-[14px] text-ink-2">{a.sentence}</p>

      {a.kind === "count" && (
        <div className="mt-4">
          <div className="num text-[48px] font-extrabold tracking-[-0.04em]">{a.count}</div>
          <ul className="mt-2 space-y-1.5">
            {Object.entries(a.by_school ?? {}).sort((x, y) => y[1] - x[1]).map(([s, n]) => (
              <li key={s} className="grid grid-cols-[120px_1fr_40px] items-center gap-3 text-[13.5px]">
                <span className="truncate text-ink-2">{s}</span>
                <span className="h-2 rounded-full bg-card-2"><span className="block h-full rounded-full bg-invert" style={{ width: `${(n / Math.max(...Object.values(a.by_school ?? { x: 1 }))) * 100}%` }} /></span>
                <span className="num text-right font-semibold">{n}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {a.kind === "children" && (
        <ol className="-mx-2 mt-3">
          {(a.rows as ChildRow[]).slice(0, 12).map((r, i) => {
            const t = a.test ? r.tests[a.test] : null;
            return (
              <li key={r.id}>
                <Link to={`/children/${r.id}`} className="flex items-center gap-3 rounded-2xl px-2 py-2 hover:bg-card-2">
                  <span className="num w-5 text-center text-[13px] font-bold text-ink-3">{i + 1}</span>
                  <Avatar name={r.name} size={36} />
                  <span className="min-w-0 flex-1"><span className="block truncate text-[15px] font-semibold">{r.name}</span><span className="block truncate text-[12.5px] text-ink-2">{r.school} · {r.klass}{r.age ? ` · ${Math.floor(r.age)} y` : ""}</span></span>
                  {a.test && t ? (
                    <span className="text-right">
                      <CellLink cite={r.cite} label={`${TEST[a.test].label} · ${r.name}`} className="num text-[14px] font-bold">{fmtValue(a.test, t.value)}</CellLink>
                      <span className="block text-[12px] text-ink-3"><Pct value={t.percentile} className="font-medium" /></span>
                    </span>
                  ) : a.spec.sort === "improved" && r.trend != null ? (
                    <span className={cx("num text-[14px] font-bold", r.trend >= 0 ? "text-mint-ink" : "text-rose-ink")}>{r.trend > 0 ? "+" : ""}{r.trend.toFixed(0)} pts</span>
                  ) : <span className="flex items-center gap-1.5">{r.flags.slice(0, 2).map((f) => <FlagChip key={f.kind} kind={f.kind} compact title={f.text} />)}<Pct value={r.composite} className="text-[14px]" /></span>}
                </Link>
              </li>
            );
          })}
        </ol>
      )}

      {a.kind === "shortlist" && (
        <ol className="mt-3 space-y-2">
          {(a.rows as Candidate[]).map((c, i) => (
            <li key={c.child_id} className="rounded-2xl bg-card-2 p-3">
              <div className="flex items-center gap-3">
                <span className="num w-5 text-center text-[14px] font-extrabold text-ink-3">{i + 1}</span>
                <Avatar name={c.name} size={34} />
                <Link to={`/children/${c.child_id}`} className="min-w-0 flex-1"><span className="block truncate font-semibold hover:underline">{c.name}</span><span className="block truncate text-[12.5px] text-ink-2">{c.school} · {c.klass}</span></Link>
                <span className="num rounded-full bg-invert px-2.5 py-1 text-[13px] font-bold text-invert-ink">{Math.round(c.score)}</span>
              </div>
              <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 pl-8 text-[13px] text-ink-2">
                {c.reasons.map((r) => <span key={r.field}>{r.label} <CellLink cite={r.cite} label={`${r.label} · ${c.name}`} className="font-semibold text-ink">{r.text}</CellLink> <span className="text-ink-3">P{Math.round(r.percentile)}</span></span>)}
              </div>
            </li>
          ))}
          <li className="pt-1 text-[13px] text-ink-2">To save picks, add this race to a meet in <Link to="/calendar" className="font-semibold text-ink underline">Meets</Link>.</li>
        </ol>
      )}

      {a.kind === "schools" && (
        <ol className="mt-3 space-y-1">
          {(a.rows as SchoolSummary[]).map((s, i) => {
            const v = a.spec.test ? s.skills[a.spec.test as TestKey] : s.composite;
            return (
              <li key={s.id}>
                <Link to={`/schools/${s.id}`} className="grid grid-cols-[22px_1fr_minmax(80px,1.2fr)_44px] items-center gap-3 rounded-xl px-2 py-2 hover:bg-card-2">
                  <span className="num text-[13px] font-bold text-ink-3">{i + 1}</span>
                  <span className="truncate text-[14.5px] font-semibold">{s.short}</span>
                  <span className="relative h-2 rounded-full bg-card-2"><span className="absolute inset-y-0 left-1/2 w-px bg-line-2" /><span className="absolute inset-y-0 left-0 rounded-full bg-invert" style={{ width: `${v ?? 0}%` }} /></span>
                  <Pct value={v} className="text-right text-[14px]" />
                </Link>
              </li>
            );
          })}
        </ol>
      )}

      {a.kind === "child" && a.child && (
        <Link to={`/children/${a.child.id}`} className="mt-4 flex items-center gap-3 rounded-2xl bg-card-2 p-3 hover:bg-line">
          <Avatar name={a.child.name} size={44} />
          <span className="min-w-0 flex-1"><span className="block font-semibold">{a.child.name}</span><span className="block text-[13px] text-ink-2">{a.child.school.short} · {a.child.klass}</span></span>
          {a.fact && <CellLink cite={a.fact.cite} label={TEST[a.fact.field].label} className="num text-[15px] font-bold">{a.fact.raw} {a.fact.unit}</CellLink>}
          <ArrowRight className="size-4 text-ink-3" />
        </Link>
      )}

      {a.kind === "compare" && a.sides && <Compare sides={a.sides} table={a.table ?? []} onPick={onPick} />}

      {childLink && (a.rows as unknown[]).length > 0 && (
        <Link to={childLink} className="mt-3 inline-flex items-center gap-1 text-[13.5px] font-semibold text-ink-2 hover:text-ink">Open the full list with these filters <ArrowRight className="size-3.5" /></Link>
      )}
      {a.kind === "empty" && <p className="mt-3 text-[14px] text-ink-2">Try a full name, or one of the suggestions.</p>}
    </Card>
  );
}

function Compare({ sides, table, onPick }: { sides: CompareSide[]; table: CompareRow[]; onPick: (side: number, id: string, name: string) => void }) {
  const unresolved = sides.some((x) => !x.child);
  if (unresolved) {
    return (
      <div className="mt-4 space-y-4">
        {sides.map((x, i) => x.child ? (
          <div key={i} className="flex items-center gap-3 rounded-2xl bg-card-2 p-3">
            <Avatar name={x.child.name} size={34} />
            <span className="min-w-0 flex-1"><span className="block truncate font-semibold">{x.child.name}</span><span className="block truncate text-[12.5px] text-ink-2">{x.child.school} · {x.child.klass}</span></span>
            <Chip tone="mint">Found</Chip>
          </div>
        ) : (
          <div key={i}>
            <p className="text-[13px] font-semibold text-ink-2">{x.matches.length ? `Which “${x.query}”?` : `No child called “${x.query}”`}</p>
            <ul className="-mx-2 mt-1">
              {x.matches.map((r) => (
                <li key={r.id}>
                  <button onClick={() => onPick(i, r.id, r.name)} className="flex w-full items-center gap-3 rounded-2xl px-2 py-2 text-left hover:bg-card-2">
                    <Avatar name={r.name} size={34} />
                    <span className="min-w-0 flex-1"><span className="block truncate text-[15px] font-semibold">{r.name}</span><span className="block truncate text-[12.5px] text-ink-2">{r.school} · {r.klass}{r.age ? ` · ${Math.floor(r.age)} y` : ""}</span></span>
                    <Pct value={r.composite} className="text-[14px]" />
                    <ArrowRight className="size-4 text-ink-3" />
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    );
  }
  const kids = sides.map((x) => x.child!);
  const cols = { gridTemplateColumns: `minmax(84px,0.8fr) repeat(${kids.length}, minmax(0,1fr))` };
  const best = Math.max(...kids.map((k) => k.composite ?? -1));
  return (
    <div className="mt-4 overflow-hidden rounded-2xl bg-card-2">
      <div className="grid items-end gap-2 p-3" style={cols}>
        <span />
        {kids.map((k) => (
          <Link key={k.id} to={`/children/${k.id}`} className="min-w-0 text-center hover:underline">
            <Avatar name={k.name} size={40} className="mx-auto" />
            <span className="mt-1.5 block truncate text-[14px] font-semibold">{k.name}</span>
            <span className="block truncate text-[12px] text-ink-2">{k.school} · {k.klass}{k.age ? ` · ${Math.floor(k.age)} y` : ""}</span>
          </Link>
        ))}
      </div>
      <div className="grid items-center gap-2 border-t border-line px-3 py-2.5" style={cols}>
        <span className="text-[13px] font-semibold text-ink-2">Overall</span>
        {kids.map((k) => (
          <span key={k.id} className={cx("rounded-xl py-1 text-center", k.composite != null && k.composite === best && kids.length > 1 && "bg-mint text-mint-ink")}>
            <Pct value={k.composite} className="text-[15px] font-bold" />
          </span>
        ))}
      </div>
      {table.map((r) => (
        <div key={r.field} className={cx("grid items-center gap-2 border-t border-line px-3 py-2.5", r.asked && "bg-card")} style={cols}>
          <span className="text-[13px] font-semibold text-ink-2">{r.label}<span className="block text-[11px] font-normal text-ink-3">{r.lower_is_better ? "lower is better" : "higher is better"}</span></span>
          {r.cells.map((c, i) => (
            <span key={i} className={cx("rounded-xl py-1 text-center", r.winner === i && "bg-mint text-mint-ink")}>
              {c && c.value != null ? (
                <>
                  <CellLink cite={c.cite} label={`${r.label} · ${kids[i].name}`} className="num text-[14px] font-bold">{fmtValue(r.field, c.value)}</CellLink>
                  <span className="block text-[12px]"><Pct value={c.percentile} className="font-medium" /></span>
                </>
              ) : <span className="text-[12.5px] text-ink-3">{c ? (c.note || c.status) : "Not tested"}</span>}
            </span>
          ))}
        </div>
      ))}
    </div>
  );
}
