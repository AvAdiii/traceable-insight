import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, UserRound } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ChildItem } from "../components/ChildItem";
import { LineChart } from "../components/LineChart";
import { Avatar, Card, Pct, SectionHead, Segmented, Skeleton, TEST, TEST_KEYS, fmtValue } from "../components/ui";
import { api, type ChildRow, type TestKey } from "../lib/api";
import type { SchoolSummary } from "./Schools";

type Prog = { id: number; label: string } & Partial<Record<TestKey, number>>;
type Detail = SchoolSummary & { progress: Prog[]; classes_detail: { klass: string; children: number; composite: number | null }[]; top: ChildRow[]; push: ChildRow[] };

export default function SchoolPage() {
  const { id } = useParams();
  const q = useQuery({ queryKey: ["school", id], queryFn: () => api<Detail>(`/api/schools/${id}`) });
  const o = useQuery({ queryKey: ["overview"], queryFn: () => api<{ progress: Prog[] }>("/api/overview") });
  const [test, setTest] = useState<TestKey>("jump");
  if (!q.data) return <Skeleton className="h-96" />;
  const s = q.data;
  const prog = o.data?.progress ?? [];
  return (
    <div className="space-y-5 md:space-y-6">
      <Link to="/schools" className="flex items-center gap-1.5 text-[14px] font-semibold text-ink-2 hover:text-ink"><ArrowLeft className="size-4" />Schools</Link>
      <div className="rounded-card bg-card p-6 shadow-card md:p-8">
        <div>
          <h1 className="text-[30px] leading-tight font-extrabold tracking-[-0.03em] md:text-[38px]">{s.short}</h1>
          <p className="text-[15px] text-ink-2">{s.name} · {s.area}</p>
          <div className="mt-4 flex flex-wrap gap-2">
            {[s.trainer && ["PT trainer", s.trainer.name], s.supervisor && ["Supervisor", s.supervisor.name]].filter(Boolean).map((x) => (
              <span key={x![0]} className="flex items-center gap-2 rounded-full bg-card-2 py-1 pr-3 pl-1 text-[13px]">
                <Avatar name={x![1]} size={26} /><span><span className="opacity-70">{x![0]}</span> <b>{x![1]}</b></span>
              </span>
            ))}
            {!s.trainer && <span className="flex items-center gap-1 text-[13px]"><UserRound className="size-4" />No coach set</span>}
          </div>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[["Children", s.children.toLocaleString("en-IN")], ["Median overall", s.composite != null ? `P${Math.round(s.composite)}` : "—"], ["Top performers", s.flags.top ?? 0], ["Need a push", s.flags.push ?? 0]].map(([l, v]) => (
          <Card key={String(l)} className="p-5"><div className="text-[13px] font-semibold text-ink-2">{l}</div><div className="num mt-1 text-[30px] font-extrabold tracking-[-0.03em]">{v}</div></Card>
        ))}
      </div>

      <div className="grid gap-5 lg:grid-cols-[1.6fr_1fr] md:gap-6">
        <Card className="p-5 md:p-6">
          <SectionHead title="Progress against the programme" />
          <Segmented size="sm" value={test} onChange={setTest} options={TEST_KEYS.map((k) => ({ value: k, label: TEST[k].skill }))} />
          <div className="mt-3">
            <LineChart xLabels={s.progress.map((p) => p.label.split(" ")[0])} main={s.progress.map((p) => p[test] ?? null)} mainLabel={`${s.short} average`}
              context={[{ id: "prog", label: "Programme average", values: s.progress.map((p) => prog.find((x) => x.id === p.id)?.[test] ?? null) }]}
              format={(v) => fmtValue(test, v)} lowerIsBetter={test === "shuttle" || test === "relay"} />
          </div>
          <p className="mt-2 text-[12.5px] text-ink-3">Orange: this school. Grey: whole programme.</p>
        </Card>
        <Card className="p-5 md:p-6">
          <SectionHead title="Classes" />
          <ul className="space-y-1">
            {s.classes_detail.map((c) => (
              <li key={c.klass}>
                <Link to={`/children?school=${s.id}&klass=${encodeURIComponent(c.klass)}`} className="grid grid-cols-[86px_1fr_40px] items-center gap-3 rounded-xl px-2 py-2 hover:bg-card-2">
                  <span className="text-[14px] font-semibold">{c.klass}</span>
                  <span className="relative h-2 rounded-full bg-card-2"><span className="absolute inset-y-0 left-1/2 w-px bg-line-2" /><span className="absolute inset-y-0 left-0 rounded-full bg-invert" style={{ width: `${c.composite ?? 0}%` }} /></span>
                  <Pct value={c.composite} className="text-right text-[13px]" />
                </Link>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <div className="grid gap-5 lg:grid-cols-2 md:gap-6">
        {([["Top performers", s.top], ["Needs a push", s.push]] as const).map(([t, rows]) => (
          <Card key={t} className="p-5">
            <SectionHead title={t} />
            <div className="-mx-2">
              {rows.map((r) => <ChildItem key={r.id} id={r.id} name={r.name} sub={`${r.klass} · ${r.gender === "Girls" ? "Girl" : "Boy"}`} flags={r.flags.map((f) => f.kind)} right={<Pct value={r.composite} className="text-[14px]" />} />)}
              {rows.length === 0 && <p className="px-2 text-[14px] text-ink-2">No one this round.</p>}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
