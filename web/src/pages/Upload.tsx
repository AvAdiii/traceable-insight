import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, FileSpreadsheet, Fingerprint, UploadCloud } from "lucide-react";
import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Choice, Input } from "../components/EventForm";
import { PageTitle } from "../components/Shell";
import { Button, Card, Illus, SectionHead, cx, fmtDate } from "../components/ui";
import { api, type Round } from "../lib/api";
import { useAct } from "../lib/hooks";

type UploadRow = { id: number; filename: string; sha256: string; size: number; round: string; uploaded_by: string | null; uploaded_at: string; summary: Record<string, number | string[]>; sheets: string[] };

export default function UploadPage() {
  const rounds = useQuery({ queryKey: ["rounds"], queryFn: () => api<Round[]>("/api/rounds") });
  const list = useQuery({ queryKey: ["uploads"], queryFn: () => api<UploadRow[]>("/api/uploads") });
  const [file, setFile] = useState<File | null>(null);
  const [roundId, setRoundId] = useState<string>("");
  const [isNew, setIsNew] = useState(false);
  const [nr, setNr] = useState({ label: "", kind: "midline", test_date: new Date().toISOString().slice(0, 10) });
  const [drag, setDrag] = useState(false);
  const [err, setErr] = useState("");
  const input = useRef<HTMLInputElement>(null);
  const up = useAct(async () => {
    const fd = new FormData();
    fd.append("file", file!);
    if (isNew) { fd.append("round_label", nr.label); fd.append("round_kind", nr.kind); fd.append("test_date", nr.test_date); }
    else fd.append("round_id", roundId);
    return api<{ id: number; filename: string; summary: Record<string, number> }>("/api/uploads", { method: "POST", body: fd });
  }, () => { setFile(null); setErr(""); });
  const result = up.data;

  return (
    <div>
      <PageTitle title="Upload sheets" />
      <div className="grid gap-5 lg:grid-cols-[1fr_1.2fr] md:gap-6">
        <Card className="bg-plate p-6 md:p-8">
          <Illus name="spreadsheets" className="mx-auto mb-5 h-44 w-full object-contain" />
          <h2 className="text-center text-[22px] font-extrabold tracking-[-0.02em] text-plate-ink">One file per round</h2>
          <p className="mx-auto mt-1 max-w-sm text-center text-[14px] text-plate-ink">Use the HRS assessment template. Anything that looks wrong goes to the Inbox, not into rankings.</p>
        </Card>

        <Card className="p-5 md:p-6">
          <form onSubmit={(e) => { e.preventDefault(); setErr(""); up.mutate(undefined, { onError: (x) => setErr((x as Error).message) }); }} className="space-y-5">
            <button type="button" onClick={() => input.current?.click()}
              onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)}
              onDrop={(e) => { e.preventDefault(); setDrag(false); const f = e.dataTransfer.files[0]; if (f) setFile(f); }}
              className={cx("flex w-full flex-col items-center gap-2 rounded-[22px] border-2 border-dashed p-8 text-center transition-colors", drag ? "border-accent bg-accent-soft" : "border-line-2 hover:border-ink-3 hover:bg-card-2")}>
              {file ? <FileSpreadsheet className="size-9 text-mint-ink" /> : <UploadCloud className="size-9 text-ink-3" />}
              <span className="text-[15px] font-semibold">{file ? file.name : "Choose an Excel or CSV file"}</span>
              <span className="text-[13px] text-ink-2">{file ? `${(file.size / 1024).toFixed(0)} KB` : "or drag it here · .xlsx, .csv"}</span>
            </button>
            <input ref={input} type="file" accept=".xlsx,.xlsm,.csv,.tsv" hidden onChange={(e) => setFile(e.target.files?.[0] ?? null)} />

            <div>
              <SectionHead title={<span className="text-[15px]">Which round is this?</span>} className="mb-2" />
              <div className="flex flex-wrap gap-1.5">
                {rounds.data?.map((r) => (
                  <button type="button" key={r.id} onClick={() => { setRoundId(String(r.id)); setIsNew(false); }} aria-pressed={!isNew && roundId === String(r.id)}
                    className={cx("h-10 rounded-full px-4 text-[14px] font-semibold", !isNew && roundId === String(r.id) ? "bg-invert text-invert-ink" : "bg-card-2 text-ink-2 hover:text-ink")}>
                    {r.label}
                  </button>
                ))}
                <button type="button" onClick={() => setIsNew(true)} aria-pressed={isNew} className={cx("h-10 rounded-full px-4 text-[14px] font-semibold", isNew ? "bg-invert text-invert-ink" : "bg-card-2 text-ink-2 hover:text-ink")}>+ New round</button>
              </div>
              {isNew && (
                <div className="mt-3 grid gap-3 sm:grid-cols-2">
                  <Input label="Round name" required value={nr.label} onChange={(e) => setNr({ ...nr, label: e.target.value })} placeholder="e.g. Baseline 2026-27" />
                  <Input label="Test date" type="date" required value={nr.test_date} onChange={(e) => setNr({ ...nr, test_date: e.target.value })} />
                  <div className="sm:col-span-2"><Choice label="Kind" value={nr.kind} onChange={(k) => setNr({ ...nr, kind: k })} options={["baseline", "midline", "endline", "custom"].map((k) => ({ value: k, label: k }))} /></div>
                </div>
              )}
            </div>
            {err && <p role="alert" className="rounded-2xl bg-rose px-4 py-3 text-[14px] font-medium text-rose-ink">{err}</p>}
            <Button type="submit" variant="primary" className="w-full" disabled={!file || (!isNew && !roundId)} loading={up.isPending}>Upload and check</Button>
          </form>

          {result && (
            <div className="mt-5 rounded-[22px] bg-mint p-4 text-mint-ink">
              <div className="flex items-center gap-2 text-[15px] font-bold text-ink"><CheckCircle2 className="size-5 text-mint-ink" />{result.filename} read</div>
              <dl className="num mt-3 grid grid-cols-2 gap-2 text-[13.5px] sm:grid-cols-4">
                {[["Rows", result.summary.rows], ["Matched to known children", result.summary.linked], ["New children", result.summary.new], ["Data checks", result.summary.issues]].map(([l, v]) => (
                  <div key={String(l)} className="rounded-xl bg-card/70 px-3 py-2"><dt className="text-[11.5px]">{l}</dt><dd className="text-[18px] font-extrabold text-ink">{v ?? 0}</dd></div>
                ))}
              </dl>
              {(result.summary.review || result.summary.issues) ? <Link to="/inbox" className="mt-3 inline-block text-[14px] font-bold text-ink underline">Review in the Inbox</Link> : null}
            </div>
          )}
        </Card>
      </div>

      <Card className="mt-6 p-5 md:p-6">
        <SectionHead title="Upload log" />
        <ul className="divide-y divide-line">
          {list.data?.map((u) => (
            <li key={u.id} className="flex flex-wrap items-center gap-x-4 gap-y-1 py-3">
              <FileSpreadsheet className="size-5 text-mint-ink" />
              <span className="min-w-0 flex-1">
                <span className="block truncate text-[14.5px] font-semibold">{u.filename}</span>
                <span className="block text-[12.5px] text-ink-2">{u.round} · {u.sheets.join(" + ")} · {u.uploaded_by ?? "—"} · {fmtDate(u.uploaded_at.slice(0, 10), { day: "numeric", month: "short", year: "numeric" })}</span>
              </span>
              <span className="num text-[13px] text-ink-2">{String(u.summary.rows ?? 0)} rows · {String(u.summary.issues ?? 0)} checks</span>
              <span className="num flex items-center gap-1 rounded-full bg-card-2 px-2.5 py-1 text-[12px] text-ink-2" title={`SHA-256 ${u.sha256}`}><Fingerprint className="size-3.5" />{u.sha256.slice(0, 10)}</span>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
