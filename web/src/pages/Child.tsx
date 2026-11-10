import { useQuery } from "@tanstack/react-query";
import { ArrowDownRight, ArrowLeft, ArrowUpRight, CalendarDays, Info, Medal, School, UserRound } from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { LineChart } from "../components/LineChart";
import { CellLink } from "../components/Receipt";
import { Avatar, Card, Chip, Empty, FLAG, FlagChip, Meter, Pct, SectionHead, Skeleton, TEST, TEST_KEYS, TONE, cx, fmtDate, fmtValue } from "../components/ui";
import { api, type ChildDetail, type TestKey } from "../lib/api";

const HELD = new Set(["suspect", "disputed", "excluded"]);

export default function Child() {
  const { id } = useParams();
  const nav = useNavigate();
  const q = useQuery({ queryKey: ["child", id], queryFn: () => api<ChildDetail>(`/api/children/${id}`) });
  if (q.isLoading) return <div className="space-y-5"><Skeleton className="h-44" /><div className="grid gap-4 md:grid-cols-4">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-44" />)}</div><Skeleton className="h-72" /></div>;
  if (!q.data) return <Empty art="file-searching" title="Child not found">They may be in a school you are not assigned to.</Empty>;
  const c = q.data;
  const last = c.rounds[c.rounds.length - 1];
  const first = c.rounds[0];
  const age = last?.age ? Math.floor(last.age) : null;
  const who = age ? `${age}-year-old ${c.gender.toLowerCase()}` : "children their age";
  const prevComp = c.rounds.length > 1 ? c.rounds[c.rounds.length - 2].composite : null;
  const trend = last?.composite != null && prevComp != null ? last.composite - prevComp : null;

  return (
    <div className="space-y-5 md:space-y-6">
      <button onClick={() => (history.length > 1 ? nav(-1) : nav("/children"))} className="flex items-center gap-1.5 text-[14px] font-semibold text-ink-2 hover:text-ink">
        <ArrowLeft className="size-4" /> Back
      </button>

      <div className="grid gap-5 lg:grid-cols-[1.35fr_1fr] md:gap-6">
        <Card className="p-5 md:p-7">
          <div className="relative flex items-start gap-4">
            <Avatar name={c.name} size={72} />
            <div className="min-w-0">
              <h1 className="text-[28px] leading-tight font-extrabold tracking-[-0.025em] md:text-[32px]">{c.name}</h1>
              <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-[14px] text-ink-2">
                <Link to={`/schools/${c.school.id}`} className="flex items-center gap-1 font-semibold text-ink hover:underline"><School className="size-4" />{c.school.short}</Link>
                <span>{c.klass}</span>
                <span>{c.gender === "Girls" ? "Girl" : "Boy"}{age ? `, ${age} years` : ""}</span>
                {c.school.trainer && <span className="flex items-center gap-1"><UserRound className="size-4" />Coach {c.school.trainer.name}</span>}
              </div>
              {c.aliases.length > 0 && <p className="mt-2 text-[13px] text-ink-3">Also written as {c.aliases.map((a) => `“${a}”`).join(", ")}</p>}
            </div>
          </div>
          <div className="relative mt-5 flex flex-wrap gap-2">
            {c.flags.length === 0 && <Chip>No flags this round</Chip>}
            {c.flags.map((f, i) => {
              const F = FLAG[f.kind];
              return (
                <span key={i} className={cx("inline-flex min-h-8 items-center gap-2 rounded-2xl px-3 py-1.5 text-[13.5px] font-semibold", TONE[F.tone])}>
                  <F.icon className="size-4 shrink-0" strokeWidth={2.3} /><span><span className="font-bold">{F.label}.</span> <span className="font-medium">{f.text}</span></span>
                </span>
              );
            })}
          </div>
        </Card>

        <Card className="flex flex-col justify-between p-5 md:p-7">
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="text-[13.5px] font-semibold text-ink-2">Overall · {last?.label}</div>
              <div className="num mt-1 text-[56px] leading-none font-extrabold tracking-[-0.04em]">{last?.composite != null ? `P${Math.round(last.composite)}` : "—"}</div>
              <div className="mt-1.5 text-[14px] text-ink-2">among {who}, all schools</div>
            </div>
            {trend !== null && (
              <span className={cx("inline-flex h-8 items-center gap-1 rounded-full px-3 text-[13px] font-bold", trend >= 0 ? "bg-mint text-mint-ink" : "bg-rose text-rose-ink")}>
                {trend >= 0 ? <ArrowUpRight className="size-4" /> : <ArrowDownRight className="size-4" />}{trend > 0 ? "+" : ""}{trend.toFixed(0)} pts
              </span>
            )}
          </div>
          <Meter value={last?.composite} tone="accent" className="mt-5 h-3" />
          <div className="mt-1.5 flex justify-between text-[11.5px] text-ink-3"><span>P0</span><span>median</span><span>P100</span></div>
          {c.rounds.length > 1 && (
            <div className="mt-3">
              <LineChart height={150} xLabels={c.rounds.map((r) => r.label.split(" ")[0])} main={c.rounds.map((r) => r.composite)} format={(v) => `P${Math.round(v)}`} mainLabel="Overall percentile" />
            </div>
          )}
        </Card>
      </div>

      {/* Skill tiles */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {TEST_KEYS.map((k) => <SkillTile key={k} k={k} c={c} />)}
      </div>

      <div className="grid gap-5 lg:grid-cols-[1.6fr_1fr] md:gap-6">
        <Card className="p-5 md:p-6">
          <SectionHead title="All rounds" />
          <p className="-mt-2 mb-4 text-[13.5px] text-ink-2">Tap a value to see its spreadsheet row.</p>
          <div className="-mx-1 overflow-x-auto">
            <table className="num w-full min-w-[560px] text-[14px]">
              <thead>
                <tr className="text-left text-[12px] font-semibold text-ink-3">
                  <th className="px-1 pb-2">Round</th>
                  {TEST_KEYS.map((k) => <th key={k} className="px-1 pb-2">{TEST[k].skill}</th>)}
                  <th className="px-1 pb-2">Height · Weight</th>
                </tr>
              </thead>
              <tbody>
                {c.rounds.map((r) => (
                  <tr key={r.id} className="border-t border-line align-top">
                    <td className="px-1 py-3">
                      <div className="font-semibold">{r.label.split(" ")[0]}</div>
                      <div className="text-[12px] text-ink-3">{fmtDate(r.test_date, { month: "short", year: "numeric" })} · {r.klass}</div>
                    </td>
                    {TEST_KEYS.map((k) => {
                      const t = r.tests[k];
                      if (!t) return <td key={k} className="px-1 py-3 text-ink-3">—</td>;
                      return (
                        <td key={k} className="px-1 py-3">
                          <CellLink cite={t.cite} label={`${TEST[k].label}, ${r.label}`} className={cx(HELD.has(t.status) && "text-peach-ink")}>
                            {t.value != null ? fmtValue(k, t.value) : t.raw || "blank"}
                          </CellLink>
                          <div className="mt-0.5 text-[12px] text-ink-3">
                            {HELD.has(t.status) ? <span className="font-semibold text-peach-ink">{t.status === "excluded" ? "Left out" : "Data check"}</span> : t.percentile != null ? `P${Math.round(t.percentile)}` : t.status === "missing" ? "Not tested" : ""}
                            {t.status === "repaired" && " · fixed typo"}{t.status === "corrected" && " · corrected"}
                          </div>
                        </td>
                      );
                    })}
                    <td className="px-1 py-3 text-ink-2">
                      {r.tests.height ? <CellLink cite={r.tests.height.cite} label={`Height, ${r.label}`}>{r.tests.height.raw} cm</CellLink> : "—"}
                      <div className="mt-0.5 text-[12px]">{r.tests.weight ? <CellLink cite={r.tests.weight.cite} label={`Weight, ${r.label}`}>{r.tests.weight.raw} kg</CellLink> : ""}</div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        <div className="space-y-5 md:space-y-6">
          <Card className="p-5 md:p-6">
            <SectionHead title="Meets & medals" />
            {c.achievements.length === 0 && c.selections.length === 0 && <p className="text-[14px] text-ink-2">Not picked for a meet yet.</p>}
            <ul className="space-y-2">
              {c.achievements.map((a, i) => (
                <li key={`a${i}`}>
                  <Link to={`/events/${a.event_id}`} className="flex items-center gap-3 rounded-2xl bg-lemon p-3 text-lemon-ink">
                    <Medal className="size-5 shrink-0" />
                    <span className="min-w-0 flex-1"><span className="block font-semibold text-ink">{a.note || `Position ${a.position}`} · {a.item}</span><span className="block text-[12.5px]">{a.event} · {fmtDate(a.date)}{a.mark ? ` · ${a.mark}` : ""}</span></span>
                  </Link>
                </li>
              ))}
              {c.selections.filter((s) => !c.achievements.some((a) => a.event_id === s.event_id)).map((s, i) => (
                <li key={`s${i}`}>
                  <Link to={`/events/${s.event_id}`} className="flex items-center gap-3 rounded-2xl bg-card-2 p-3">
                    <CalendarDays className="size-5 shrink-0 text-ink-2" />
                    <span className="min-w-0 flex-1"><span className="block font-semibold">{s.status === "reserve" ? "Reserve" : "Selected"} · {s.item}</span><span className="block text-[12.5px] text-ink-2">{s.event} · {fmtDate(s.date)}</span></span>
                  </Link>
                </li>
              ))}
            </ul>
          </Card>

          {c.issues.length > 0 && (
            <Card className="p-5 md:p-6">
              <SectionHead title="Data checks" action={<Link to="/inbox" className="text-[13px] font-semibold text-ink-2 hover:text-ink">Inbox</Link>} />
              <ul className="space-y-2">
                {c.issues.map((i) => (
                  <li key={i.key} className="rounded-2xl bg-peach p-3 text-[13.5px] text-peach-ink"><span className="font-semibold text-ink">{i.title}</span><span className="mt-0.5 block">{i.detail}</span></li>
                ))}
              </ul>
            </Card>
          )}

          <Card className="p-5 md:p-6">
            <SectionHead title="Record" />
            <dl className="grid grid-cols-2 gap-3 text-[14px]">
              <div><dt className="text-[12px] text-ink-3">Parent</dt><dd className="font-semibold">{c.parent || "—"}</dd></div>
              <div><dt className="text-[12px] text-ink-3">Date of birth</dt><dd className="font-semibold">{c.dob ? fmtDate(c.dob, { day: "numeric", month: "short", year: "numeric" }) : "—"}</dd></div>
              <div><dt className="text-[12px] text-ink-3">First tested</dt><dd className="font-semibold">{first?.label}</dd></div>
              <div><dt className="text-[12px] text-ink-3">Programme id</dt><dd className="num font-semibold">{c.id}</dd></div>
            </dl>
            <p className="mt-3 flex gap-2 text-[12.5px] text-ink-3"><Info className="size-4 shrink-0" />Percentiles compare with children of the same gender and age across every school, in the same round.</p>
          </Card>
        </div>
      </div>
    </div>
  );
}

function SkillTile({ k, c }: { k: TestKey; c: ChildDetail }) {
  const T = TEST[k];
  const last = c.rounds[c.rounds.length - 1];
  const t = last?.tests[k];
  const p = c.progress[k];
  const held = t && HELD.has(t.status);
  return (
    <div className="rounded-tile bg-card p-4 shadow-card">
      <div className="relative flex items-center gap-2.5">
        <span className={cx("grid size-9 place-items-center rounded-xl", TONE[T.tone])}><T.icon className="size-[18px]" /></span>
        <span className="text-[13.5px] font-semibold text-ink-2">{T.label}</span>
      </div>
      <div className="relative mt-3 flex items-baseline gap-2">
        <span className="num text-[30px] leading-none font-extrabold tracking-[-0.03em] text-ink">
          {t ? <CellLink cite={t.cite} label={`${T.label}, ${last.label}`}>{t.value != null ? fmtValue(k, t.value) : "—"}</CellLink> : "—"}
        </span>
      </div>
      <div className="relative mt-1.5 text-[13px] text-ink-2">
        {held ? <span className="font-semibold text-peach-ink">Waiting for a data check: {t!.note}</span>
          : t?.percentile != null ? <><Pct value={t.percentile} className="text-ink" /> among {t.pool}</> : t?.note || "Not tested this round"}
      </div>
      {p && (
        <span className={cx("relative mt-3 inline-flex h-7 items-center gap-1 rounded-full px-2.5 text-[12px] font-bold", p.better ? "bg-mint text-mint-ink" : "bg-rose text-rose-ink")}>
          {p.better ? <ArrowUpRight className="size-3.5" /> : <ArrowDownRight className="size-3.5" />}
          {fmtValue(k, p.from)} → {fmtValue(k, p.to)}
        </span>
      )}
      {!p && c.flags.some((f) => f.kind === "missing") && <span className="relative mt-3 inline-flex"><FlagChip kind="missing" /></span>}
    </div>
  );
}
