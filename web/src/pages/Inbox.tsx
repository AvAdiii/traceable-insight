import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, Copy, FileSpreadsheet, Info, Layers, Ruler, Undo2, UserSearch, type LucideIcon } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { useReceipt } from "../components/Receipt";
import { PageTitle } from "../components/Shell";
import { Button, Card, Chip, Empty, Segmented, Skeleton, cx, useToast } from "../components/ui";
import { api, type Issue } from "../lib/api";
import { useAct, useSchoolName } from "../lib/hooks";

const KIND: Record<string, { label: string; icon: LucideIcon }> = {
  name: { label: "Name to confirm", icon: UserSearch },
  class_copy: { label: "Class pasted twice", icon: Copy },
  conflict: { label: "Entered twice", icon: Layers },
  placeholder: { label: "Placeholder values", icon: AlertTriangle },
  unit: { label: "Wrong unit", icon: Ruler },
  implausible: { label: "Value looks wrong", icon: AlertTriangle },
  outlier: { label: "Unusual for age", icon: AlertTriangle },
  sheet_disagree: { label: "Sheets disagree", icon: FileSpreadsheet },
  repaired: { label: "Typo fixed", icon: Info },
  dob: { label: "Date of birth", icon: Info },
  duplicate_rows: { label: "Repeated rows", icon: Copy },
};
const SEV = { high: { label: "Blocks ranking", tone: "rose" as const }, medium: { label: "Held from ranking", tone: "peach" as const }, low: { label: "For your info", tone: "slate" as const } };

export default function Inbox() {
  const [status, setStatus] = useState<"open" | "resolved">("open");
  const [kind, setKind] = useState<string | null>(null);
  const q = useQuery({ queryKey: ["inbox", status, kind], queryFn: () => api<{ counts: Record<string, number>; open: number; resolved: number; rows: Issue[] }>(`/api/inbox?status=${status}${kind ? `&kind=${kind}` : ""}`) });
  return (
    <div className="mx-auto max-w-4xl">
      <PageTitle title="Inbox" sub="Problems in the sheets. Files are never edited; your choices are saved and can be undone."
        action={<Segmented value={status} onChange={(v) => { setStatus(v); setKind(null); }} options={[{ value: "open", label: `Open · ${q.data?.open ?? "…"}` }, { value: "resolved", label: `Decided · ${q.data?.resolved ?? "…"}` }]} />} />
      {status === "open" && q.data && (
        <div className="-mx-4 mb-5 flex gap-2 overflow-x-auto px-4 no-scrollbar md:mx-0 md:flex-wrap md:px-0">
          <button onClick={() => setKind(null)} className={cx("h-9 shrink-0 rounded-full px-4 text-[13.5px] font-semibold", !kind ? "bg-invert text-invert-ink" : "bg-card text-ink-2 shadow-card")}>All</button>
          {Object.entries(q.data.counts).sort((a, b) => b[1] - a[1]).map(([k, n]) => {
            const K = KIND[k] ?? { label: k, icon: Info };
            return (
              <button key={k} onClick={() => setKind(kind === k ? null : k)} className={cx("flex h-9 shrink-0 items-center gap-1.5 rounded-full px-3.5 text-[13.5px] font-semibold", kind === k ? "bg-invert text-invert-ink" : "bg-card text-ink-2 shadow-card hover:text-ink")}>
                <K.icon className="size-4" />{K.label}<span className="num opacity-70">{n}</span>
              </button>
            );
          })}
        </div>
      )}
      {q.isLoading && <div className="space-y-3">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-40" />)}</div>}
      {q.data && q.data.rows.length === 0 && (
        <Card><Empty art="done-checking" title={status === "open" ? "All clear" : "No decisions yet"}>{status === "open" ? "Every sheet value is either fine or decided. Rankings use everything." : "Decisions you make on open items show here, with undo."}</Empty></Card>
      )}
      <div className="space-y-3">
        {q.data?.rows.map((i) => <IssueCard key={i.key} i={i} />)}
      </div>
    </div>
  );
}

function IssueCard({ i }: { i: Issue }) {
  const toast = useToast();
  const receipt = useReceipt();
  const school = useSchoolName();
  const [val, setVal] = useState("");
  const [inputFor, setInputFor] = useState<string | null>(null);
  const undo = useAct(() => api("/api/inbox/undo", { method: "POST", json: { key: i.key } }));
  const resolve = useAct((v: { option_id: string; value?: number }) => api<{ open: number }>("/api/inbox/resolve", { method: "POST", json: { key: i.key, ...v } }),
    (r) => toast({ text: `Saved. ${r.open} left; rankings updated.`, action: { label: "Undo", run: () => undo.mutate(undefined) } }));
  const K = KIND[i.kind] ?? { label: i.kind, icon: Info };
  const S = SEV[i.severity];
  const chosen = i.resolved ? i.options.find((o) => JSON.stringify(o.payload) === JSON.stringify(Object.fromEntries(Object.entries(i.resolution).filter(([k]) => k !== "value")))) : null;
  return (
    <Card as="article" className="p-5">
      <div className="flex flex-wrap items-center gap-2">
        <Chip tone={S.tone} icon={K.icon}>{K.label}</Chip>
        <span className="text-[12.5px] font-semibold text-ink-3">{S.label}{i.school_id ? ` · ${school(i.school_id)}` : ""}{i.count > 1 ? ` · ${i.count} rows` : ""}</span>
      </div>
      <h3 className="mt-2.5 text-[16.5px] leading-snug font-bold tracking-[-0.01em]">{i.title}</h3>
      <p className="mt-1 text-[14px] text-ink-2">{i.detail}</p>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        {i.record_ids.length > 0 && <Button size="sm" icon={FileSpreadsheet} onClick={() => receipt({ record_id: i.record_ids[0], field: i.field || null, label: i.title })}>See the row</Button>}
        {i.child_id && <Link to={`/children/${i.child_id}`} className="h-9 rounded-full px-3.5 text-[13px] leading-9 font-semibold text-ink-2 hover:bg-card-2 hover:text-ink">Child profile</Link>}
      </div>
      {i.resolved ? (
        <div className="mt-4 flex flex-wrap items-center justify-between gap-2 rounded-2xl bg-mint px-4 py-3 text-mint-ink">
          <span className="flex items-center gap-2 text-[14px] font-semibold"><CheckCircle2 className="size-4" />{chosen?.label ?? "Decided"}{typeof i.resolution.value === "number" ? `: ${i.resolution.value}` : ""}</span>
          <Button size="sm" icon={Undo2} onClick={() => undo.mutate(undefined)} loading={undo.isPending} className="bg-card">Undo</Button>
        </div>
      ) : (
        <div className="mt-4 border-t border-line pt-4">
          <div className="flex flex-wrap gap-2">
            {i.options.map((o, n) => (
              <Button key={o.id} size="sm" variant={n === 0 ? "primary" : "secondary"} loading={resolve.isPending && resolve.variables?.option_id === o.id}
                onClick={() => (o.input ? setInputFor(o.id) : resolve.mutate({ option_id: o.id }))}>
                {o.label}
              </Button>
            ))}
          </div>
          {inputFor && (
            <form className="mt-3 flex gap-2" onSubmit={(e) => { e.preventDefault(); if (val) resolve.mutate({ option_id: inputFor, value: Number(val) }); }}>
              <input autoFocus inputMode="decimal" value={val} onChange={(e) => setVal(e.target.value)} placeholder="Correct value" aria-label="Correct value"
                className="num h-10 w-40 rounded-xl bg-card-2 px-3 outline-none focus:ring-2 focus:ring-accent/50" />
              <Button size="sm" variant="primary" type="submit">Save</Button>
            </form>
          )}
        </div>
      )}
    </Card>
  );
}
