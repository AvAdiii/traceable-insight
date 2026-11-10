import { useQuery } from "@tanstack/react-query";
import { AlertCircle, LayoutGrid, Table2, UserRound } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { PageTitle } from "../components/Shell";
import { Avatar, Card, FLAG, Pct, Segmented, Skeleton, TEST, TEST_KEYS, cx } from "../components/ui";
import { api, type FlagKind, type SchoolBrief, type TestKey } from "../lib/api";

export type SchoolSummary = SchoolBrief & { children: number; composite: number | null; skills: Partial<Record<TestKey, number>>; flags: Partial<Record<FlagKind, number>>; issues: number; classes: string[] };

export default function Schools() {
  const q = useQuery({ queryKey: ["schools"], queryFn: () => api<SchoolSummary[]>("/api/schools") });
  const [view, setView] = useState<"cards" | "table">("cards");
  return (
    <div>
      <PageTitle title="Schools"
        action={<Segmented value={view} onChange={setView} options={[{ value: "cards", label: <span className="flex items-center gap-1.5"><LayoutGrid className="size-4" />Cards</span> }, { value: "table", label: <span className="flex items-center gap-1.5"><Table2 className="size-4" />Compare</span> }]} />} />
      {q.isLoading && <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">{Array.from({ length: 6 }, (_, i) => <Skeleton key={i} className="h-72" />)}</div>}
      {view === "cards" ? (
        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {q.data?.map((s, i) => <SchoolCard key={s.id} s={s} rank={i + 1} />)}
        </div>
      ) : q.data && (
        <Card className="overflow-x-auto p-2">
          <table className="num w-full min-w-[760px] text-[14px]">
            <thead><tr className="text-left text-[12px] font-semibold text-ink-3">
              <th className="p-3">School</th><th className="p-3">Coach</th><th className="p-3">Children</th><th className="p-3">Overall</th>
              {TEST_KEYS.map((k) => <th key={k} className="p-3">{TEST[k].skill}</th>)}<th className="p-3">Top</th><th className="p-3">Need push</th><th className="p-3">Checks</th>
            </tr></thead>
            <tbody>
              {q.data.map((s) => (
                <tr key={s.id} className="border-t border-line hover:bg-card-2">
                  <td className="p-3 font-semibold"><Link to={`/schools/${s.id}`} className="hover:underline">{s.short}</Link></td>
                  <td className="p-3 text-ink-2">{s.trainer?.name ?? "—"}</td>
                  <td className="p-3">{s.children}</td>
                  <td className="p-3 font-bold"><Pct value={s.composite} /></td>
                  {TEST_KEYS.map((k) => <td key={k} className="p-3"><Pct value={s.skills[k]} className="font-medium" /></td>)}
                  <td className="p-3">{s.flags.top ?? 0}</td><td className="p-3">{s.flags.push ?? 0}</td>
                  <td className={cx("p-3", s.issues && "font-semibold text-peach-ink")}>{s.issues}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}

function SchoolCard({ s, rank }: { s: SchoolSummary; rank: number }) {
  return (
    <Link to={`/schools/${s.id}`} className="group block">
      <Card className="h-full overflow-hidden transition-transform duration-200 group-hover:-translate-y-0.5">
        <div className="p-5">
          <span className="num mb-3 inline-block rounded-full bg-card-2 px-2.5 py-1 text-[12px] font-bold text-ink-2">#{rank}</span>
          <h3 className="text-[18px] leading-tight font-bold tracking-[-0.01em]">{s.short}</h3>
          <p className="truncate text-[13px] text-ink-2">{s.name} · {s.area}</p>
          <div className="mt-3 flex items-center gap-2 text-[13px] text-ink-2">
            {s.trainer ? <><Avatar name={s.trainer.name} size={26} /><span>Coach <b className="font-semibold text-ink">{s.trainer.name}</b></span></> : <><UserRound className="size-4" />No coach set</>}
          </div>
          <div className="mt-4 flex items-end justify-between">
            <div><div className="num text-[30px] leading-none font-extrabold tracking-[-0.03em]"><Pct value={s.composite} /></div><div className="mt-1 text-[12px] text-ink-3">median overall · {s.children} children</div></div>
            <div className="flex gap-1.5">
              {(["top", "push"] as FlagKind[]).map((k) => {
                const F = FLAG[k];
                return <span key={k} title={F.label} className="flex h-7 items-center gap-1 rounded-full bg-card-2 px-2.5 text-[12.5px] font-semibold"><F.icon className="size-3.5" />{s.flags[k] ?? 0}</span>;
              })}
            </div>
          </div>
          <div className="mt-4 space-y-2">
            {TEST_KEYS.map((k) => (
              <div key={k} className="grid grid-cols-[86px_1fr_36px] items-center gap-2 text-[12.5px]">
                <span className="text-ink-2">{TEST[k].skill}</span>
                <span className="relative h-1.5 rounded-full bg-card-2"><span className="absolute inset-y-0 left-1/2 w-px bg-line-2" /><span className="absolute inset-y-0 left-0 rounded-full bg-invert" style={{ width: `${s.skills[k] ?? 0}%` }} /></span>
                <Pct value={s.skills[k]} className="text-right" />
              </div>
            ))}
          </div>
          {s.issues > 0 && <div className="mt-4 flex items-center gap-1.5 rounded-xl bg-peach px-3 py-2 text-[12.5px] font-semibold text-peach-ink"><AlertCircle className="size-4" />{s.issues} data checks open</div>}
        </div>
      </Card>
    </Link>
  );
}
