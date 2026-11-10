import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";
import { FilterButton, FlagRow, type Filters } from "../components/Filters";
import { PageTitle } from "../components/Shell";
import { Avatar, Card, Empty, FlagChip, Meter, Pct, Segmented, Skeleton, TEST, TEST_KEYS, cx, fmtValue } from "../components/ui";
import { api, qs, type ChildRow, type TestKey } from "../lib/api";
import { useMeta } from "../lib/hooks";

const SORTS = [{ value: "best", label: "Best" }, { value: "worst", label: "Lowest" }, { value: "improved", label: "Improved" }, { value: "name", label: "A–Z" }];

export default function Children() {
  const [sp, setSp] = useSearchParams();
  const meta = useMeta();
  const f: Filters = Object.fromEntries(sp.entries());
  const set = (p: Partial<Filters>) => {
    const n = new URLSearchParams(sp);
    Object.entries(p).forEach(([k, v]) => (v ? n.set(k, v) : n.delete(k)));
    setSp(n, { replace: true });
  };
  const limit = Number(sp.get("limit") ?? 60);
  const q = useQuery({
    queryKey: ["children", f, limit],
    queryFn: () => api<{ total: number; rows: ChildRow[] }>(`/api/children${qs({ ...f, sort: f.sort ?? "best", limit })}`),
    placeholderData: (prev) => prev,
  });
  const count = ["school", "klass", "gender", "age_min", "age_max", "round_id", "test", "coach"].filter((k) => sp.get(k)).length;
  const test = f.test as TestKey | undefined;
  const sort = f.sort ?? "best";

  return (
    <div>
      <PageTitle title="Children"
        sub={q.data ? `${q.data.total.toLocaleString("en-IN")} children, compared with others of the same age and gender` : " "} />
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <label className="flex h-11 min-w-0 flex-1 basis-64 items-center gap-2 rounded-full bg-card px-4 shadow-card focus-within:ring-2 focus-within:ring-accent/50">
          <Search className="size-[18px] text-ink-3" />
          <input value={f.q ?? ""} onChange={(e) => set({ q: e.target.value })} placeholder="Search name or parent" aria-label="Search children"
            className="h-full min-w-0 flex-1 bg-transparent text-[15px] outline-none placeholder:text-ink-3" />
        </label>
        <Segmented value={sort} onChange={(v) => set({ sort: v })} options={SORTS} />
        <FilterButton f={f} set={set} meta={meta.data} count={count} />
      </div>
      <div className="mb-3 flex items-center gap-2 overflow-x-auto no-scrollbar">
        <span className="shrink-0 text-[12.5px] font-semibold text-ink-3">Rank by</span>
        <button onClick={() => set({ test: "" })} className={cx("h-8 shrink-0 rounded-full px-3 text-[13px] font-semibold", !test ? "bg-invert text-invert-ink" : "text-ink-2 hover:bg-card")}>Overall</button>
        {TEST_KEYS.map((k) => {
          const T = TEST[k];
          return (
            <button key={k} onClick={() => set({ test: k })} className={cx("flex h-8 shrink-0 items-center gap-1.5 rounded-full px-3 text-[13px] font-semibold", test === k ? "bg-invert text-invert-ink" : "text-ink-2 hover:bg-card")}>
              <T.icon className="size-3.5" />{T.label}
            </button>
          );
        })}
      </div>
      <div className="mb-5"><FlagRow value={f.flag} onChange={(v) => set({ flag: v ?? "" })} /></div>

      <Card className="overflow-hidden">
        <div className="hidden grid-cols-[48px_minmax(220px,2.2fr)_70px_minmax(140px,1.3fr)_repeat(4,minmax(78px,0.8fr))_minmax(110px,1fr)] items-center gap-3 border-b border-line px-5 py-3 text-[12px] font-semibold text-ink-3 lg:grid">
          <span>#</span><span>Child</span><span>Age</span><span>Overall</span>
          {TEST_KEYS.map((k) => <span key={k} className={cx(test === k && "text-ink")}>{TEST[k].skill}</span>)}
          <span>Flags</span>
        </div>
        {q.isLoading && <div className="space-y-2 p-4">{Array.from({ length: 8 }, (_, i) => <Skeleton key={i} className="h-14" />)}</div>}
        {q.data && q.data.rows.length === 0 && (
          <Empty art="file-searching" title="No children match">Try removing a filter.</Empty>
        )}
        <ol>
          {q.data?.rows.map((r, i) => (
            <li key={r.id} className="border-b border-line last:border-0">
              <Link to={`/children/${r.id}`} className="grid grid-cols-[32px_1fr_auto] items-center gap-3 px-4 py-3 transition-colors hover:bg-card-2 lg:grid-cols-[48px_minmax(220px,2.2fr)_70px_minmax(140px,1.3fr)_repeat(4,minmax(78px,0.8fr))_minmax(110px,1fr)] lg:px-5">
                <span className="num text-center text-[14px] font-bold text-ink-3">
                  {sort === "best" && i < 3 && !f.q ? <span className={cx("mx-auto grid size-7 place-items-center rounded-full text-[13px]", i === 0 ? "bg-lemon text-lemon-ink" : "bg-slate text-slate-ink")}>{i + 1}</span> : i + 1}
                </span>
                <span className="flex min-w-0 items-center gap-3">
                  <Avatar name={r.name} />
                  <span className="min-w-0">
                    <span className="block truncate text-[15px] font-semibold">{r.name}</span>
                    <span className="block truncate text-[13px] text-ink-2">{r.school} · {r.klass} · {r.gender === "Girls" ? "Girl" : "Boy"}{r.age ? <span className="lg:hidden"> · {Math.floor(r.age)} y</span> : null}</span>
                  </span>
                </span>
                {/* phone: one number */}
                <span className="flex flex-col items-end gap-1 lg:hidden">
                  <span className="num rounded-full bg-card-2 px-2.5 py-1 text-[14px] font-bold">
                    {test ? <Pct value={r.tests[test]?.percentile} /> : sort === "improved" && r.trend !== null ? `${r.trend > 0 ? "+" : ""}${r.trend.toFixed(0)}` : <Pct value={r.composite} />}
                  </span>
                  {test && <span className="num text-[12px] text-ink-2">{fmtValue(test, r.tests[test]?.value)}</span>}
                  {!test && r.flags.length > 0 && <span className="flex gap-1">{[...new Set(r.flags.map((x) => x.kind))].slice(0, 3).map((k) => <FlagChip key={k} kind={k} compact />)}</span>}
                </span>
                <span className="num hidden text-[14px] text-ink-2 lg:block">{r.age ? Math.floor(r.age) : "—"}</span>
                <span className="hidden items-center gap-2.5 lg:flex">
                  <Meter value={r.composite} className="flex-1" />
                  <Pct value={r.composite} className="w-9 text-right text-[14px]" />
                </span>
                {TEST_KEYS.map((k) => {
                  const t = r.tests[k];
                  const held = t && (t.status === "suspect" || t.status === "disputed");
                  return (
                    <span key={k} className={cx("hidden flex-col lg:flex", test === k ? "text-ink" : "text-ink-2")} title={held ? "Waiting for a data check" : undefined}>
                      <span className={cx("num text-[14px]", test === k && "font-bold")}>{held ? <span className="text-peach-ink">check</span> : <Pct value={t?.percentile} className="font-medium" />}</span>
                      <span className="num text-[12px] text-ink-3">{fmtValue(k, t?.value)}</span>
                    </span>
                  );
                })}
                <span className="hidden gap-1 lg:flex">
                  {[...new Set(r.flags.map((x) => x.kind))].map((k) => <FlagChip key={k} kind={k} compact title={r.flags.find((x) => x.kind === k)?.text} />)}
                  {sort === "improved" && r.trend !== null && <span className={cx("num ml-1 text-[13px] font-bold", r.trend >= 0 ? "text-mint-ink" : "text-rose-ink")}>{r.trend > 0 ? "+" : ""}{r.trend.toFixed(0)}</span>}
                </span>
              </Link>
            </li>
          ))}
        </ol>
        {q.data && q.data.total > q.data.rows.length && (
          <div className="border-t border-line p-4 text-center">
            <button onClick={() => set({ limit: String(limit + 60) } as Partial<Filters>)} className="h-10 rounded-full bg-card-2 px-5 text-[14px] font-semibold hover:bg-line">
              Show more · {q.data.total - q.data.rows.length} left
            </button>
          </div>
        )}
      </Card>
    </div>
  );
}
