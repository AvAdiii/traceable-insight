import { useQuery } from "@tanstack/react-query";
import { Cpu, Download, Laptop, ListFilter, ShieldCheck, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { PageTitle } from "../components/Shell";
import { Button, Card, Chip, SectionHead, TEST, TEST_KEYS, cx, useToast } from "../components/ui";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useAct, useMeta } from "../lib/hooks";
import { MODELS, OLLAMA_MODEL, load, ollamaAvailable, ollamaModelName, preferredModel, remove, setPreferredModel } from "../lib/llm";
import { useEngine } from "./Ask";

type ProgSettings = { weights: Record<string, number>; flags: Record<string, number>; placeholder_share: number };

export default function SettingsPage() {
  const { user } = useAuth();
  const isManager = user?.role === "manager";
  return (
    <div className="mx-auto max-w-4xl space-y-5 md:space-y-6">
      <PageTitle title="Settings" />
      <AiCard />
      <RankingCard editable={isManager} />
      <SchoolsCard editable={isManager} />
      <Card className="flex gap-4 p-5 md:p-6">
        <ShieldCheck className="size-6 shrink-0 text-mint-ink" />
        <div className="text-[14px] text-ink-2">
          <h2 className="mb-1 text-[16px] font-bold text-ink">Privacy</h2>
          Children’s data lives in the programme’s database and the uploaded files. The language model, on this device or on a laptop, only receives your question and the list of test and school names; it never receives names, dates of birth or results. The demo workspace uses synthetic children.
        </div>
      </Card>
    </div>
  );
}

function AiCard() {
  const s = useEngine();
  const [choice, setChoice] = useState(preferredModel());
  const [ollama, setOllama] = useState<boolean | null>(null);
  useEffect(() => { void ollamaAvailable().then(setOllama); }, []);
  return (
    <Card id="ai" className="relative overflow-hidden p-5 md:p-6">
      <SectionHead title="Ask: language model" />
      <p className="-mt-1 max-w-xl text-[14px] text-ink-2">Runs inside this browser with WebGPU, offline after one download. If it is not available, Ask uses a Qwen model on this laptop through Ollama (any installed Qwen, preferring {OLLAMA_MODEL}), then plain rules.</p>
      <div className="mt-4 grid gap-2 sm:grid-cols-3">
        {MODELS.map((m) => (
          <button key={m.id} onClick={() => { setChoice(m.id); setPreferredModel(m.id); }} aria-pressed={choice === m.id}
            className={cx("rounded-[20px] p-4 text-left transition-colors", choice === m.id ? "bg-invert text-invert-ink" : "bg-card-2 hover:bg-line")}>
            <div className="text-[15px] font-bold">{m.label}</div>
            <div className={cx("mt-0.5 text-[12px]", choice === m.id ? "opacity-75" : "text-ink-2")}>{m.id.split("-q4")[0].replace(/-/g, " ")}</div>
            <div className={cx("mt-2 text-[12px]", choice === m.id ? "opacity-75" : "text-ink-3")}>{m.size}</div>
            <div className={cx("text-[12px]", choice === m.id ? "opacity-75" : "text-ink-3")}>{m.note}</div>
          </button>
        ))}
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-3">
        {s.status === "unsupported" ? <Chip tone="slate" icon={ListFilter}>{s.reason}</Chip>
          : s.status === "ready" && s.model === choice ? <><Chip tone="mint" icon={Cpu}>Ready on this device</Chip><Button size="sm" variant="ghost" icon={Trash2} onClick={() => void remove(choice)}>Remove download</Button></>
            : s.status === "loading" ? (
              <div className="w-full max-w-md">
                <div className="mb-1 flex justify-between text-[12.5px] text-ink-2"><span className="truncate pr-2">{s.text}</span><span className="num">{Math.round(s.progress * 100)}%</span></div>
                <div className="h-2 rounded-full bg-card-2"><div className="h-full rounded-full bg-accent transition-[width]" style={{ width: `${s.progress * 100}%` }} /></div>
              </div>
            ) : <Button variant="primary" icon={Download} onClick={() => void load(choice)}>{s.status === "ready" ? "Switch to this model" : "Download and start"}</Button>}
        {s.status === "error" && <span className="text-[13px] text-rose-ink">{s.message}</span>}
      </div>
      <div className="mt-4 flex items-center gap-2 text-[13px] text-ink-2">
        <Laptop className="size-4" />Laptop model: {ollama === null ? "checking…" : ollama ? <b className="text-mint-ink">{ollamaModelName()} ready</b> : <>not found. Run <code className="rounded bg-card-2 px-1.5">ollama pull {OLLAMA_MODEL}</code> and start Ollama with <code className="rounded bg-card-2 px-1.5">OLLAMA_ORIGINS=*</code></>}
      </div>
    </Card>
  );
}

function RankingCard({ editable }: { editable: boolean }) {
  const toast = useToast();
  const q = useQuery({ queryKey: ["settings"], queryFn: () => api<ProgSettings>("/api/settings") });
  const [w, setW] = useState<Record<string, number> | null>(null);
  const [f, setF] = useState<Record<string, number> | null>(null);
  useEffect(() => { if (q.data) { setW(q.data.weights); setF(q.data.flags); } }, [q.data]);
  const save = useAct(() => api("/api/settings", { method: "PUT", json: { weights: w, flags: f } }), () => toast({ text: "Saved. Every ranking and flag was recomputed." }));
  if (!w || !f) return null;
  const total = Object.values(w).reduce((a, b) => a + b, 0) || 1;
  const FL: [string, string, string][] = [["top", "Top performer at overall", "P"], ["push", "Needs a push at overall", "P"], ["improved", "Most improved: gain of", "pts"], ["declining", "Declining: drop of", "pts"]];
  return (
    <Card className="p-5 md:p-6">
      <SectionHead title="Ranking" />
      <p className="-mt-1 text-[14px] text-ink-2">Overall score is the weighted mean of a child’s four test percentiles (same gender and age, all schools).</p>
      <div className="mt-4 space-y-3">
        {TEST_KEYS.map((k) => (
          <label key={k} className="grid grid-cols-[130px_1fr_48px] items-center gap-3 text-[14px]">
            <span className="flex items-center gap-2 font-semibold">{(() => { const I = TEST[k].icon; return <I className="size-4" />; })()}{TEST[k].skill}</span>
            <input type="range" min={0} max={3} step={0.25} value={w[k]} disabled={!editable} onChange={(e) => setW({ ...w, [k]: +e.target.value })} className="accent-[var(--accent)]" />
            <span className="num text-right text-ink-2">{Math.round((w[k] / total) * 100)}%</span>
          </label>
        ))}
      </div>
      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        {FL.map(([k, l, u]) => (
          <label key={k} className="flex items-center justify-between gap-3 rounded-2xl bg-card-2 px-4 py-2.5 text-[14px]">
            <span>{l}</span>
            <span className="flex items-center gap-1"><input type="number" disabled={!editable} value={f[k]} onChange={(e) => setF({ ...f, [k]: +e.target.value })} className="num h-9 w-16 rounded-xl bg-card px-2 text-center outline-none focus:ring-2 focus:ring-accent/50" /><span className="text-ink-3">{u}</span></span>
          </label>
        ))}
      </div>
      {editable ? <Button variant="primary" className="mt-5" loading={save.isPending} onClick={() => save.mutate(undefined)}>Save and recompute</Button>
        : <p className="mt-4 text-[13px] text-ink-3">Only the programme manager can change these.</p>}
    </Card>
  );
}

function SchoolsCard({ editable }: { editable: boolean }) {
  const meta = useMeta();
  const patch = useAct((v: { id: string; trainer_id?: number | null; supervisor_id?: number | null }) => api(`/api/schools/${v.id}`, { method: "PATCH", json: v }));
  const coaches = meta.data?.coaches ?? [];
  return (
    <Card className="p-5 md:p-6">
      <SectionHead title="Schools and coaches" />
      <p className="-mt-1 mb-4 text-[14px] text-ink-2">The template has no coach column, so each school is linked to its PT trainer and supervisor here. This powers the coach filter.</p>
      <ul className="divide-y divide-line">
        {meta.data?.schools.map((s) => (
          <li key={s.id} className="grid gap-2 py-3 sm:grid-cols-[1.2fr_1fr_1fr] sm:items-center">
            <span><span className="block text-[14.5px] font-semibold">{s.short}</span><span className="block text-[12.5px] text-ink-3">{s.area}</span></span>
            {(["trainer", "supervisor"] as const).map((role) => (
              <select key={role} disabled={!editable} aria-label={`${role} for ${s.short}`} value={s[role]?.id ?? ""}
                onChange={(e) => patch.mutate({ id: s.id, [`${role}_id`]: e.target.value ? +e.target.value : null })}
                className="h-10 rounded-xl bg-card-2 px-3 text-[14px] outline-none disabled:opacity-70">
                <option value="">No {role === "trainer" ? "PT trainer" : "supervisor"}</option>
                {coaches.filter((c) => c.role === role).map((c) => <option key={c.id} value={c.id}>{role === "trainer" ? "Trainer: " : "Supervisor: "}{c.name}</option>)}
              </select>
            ))}
          </li>
        ))}
      </ul>
    </Card>
  );
}
