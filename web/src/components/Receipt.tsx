import { useQuery } from "@tanstack/react-query";
import { FileSpreadsheet, Fingerprint, Layers } from "lucide-react";
import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { api, type Cite } from "../lib/api";
import { Segmented, Sheet, Skeleton, cx, fmtDate } from "./ui";

type Target = { record_id: number; field?: string | null; col?: string | null; label?: string };
const Ctx = createContext<(t: Target) => void>(() => {});
export const useReceipt = () => useContext(Ctx);

type ReceiptData = {
  file: string; sha256: string; uploaded_at: string; round: { label: string; test_date: string }; sheet: string;
  header_row: number; headers: string[]; row: number; col: string | null; field: string | null;
  rows: { row: number; cells: string[]; cited: boolean }[];
  twin: { sheet: string; row: number; headers: string[]; cells: string[] } | null;
};

const letter = (i: number) => {
  let s = "";
  for (let n = i + 1; n > 0; n = Math.floor((n - 1) / 26)) s = String.fromCharCode(65 + ((n - 1) % 26)) + s;
  return s;
};

export function ReceiptProvider({ children }: { children: ReactNode }) {
  const [target, setTarget] = useState<Target | null>(null);
  const open = useCallback((t: Target) => setTarget(t), []);
  return (
    <Ctx.Provider value={open}>
      {children}
      <Sheet open={!!target} onClose={() => setTarget(null)} wide title={<span className="flex items-center gap-2"><FileSpreadsheet className="size-5 text-mint-ink" /> Where this came from</span>}>
        {target && <ReceiptBody t={target} />}
      </Sheet>
    </Ctx.Provider>
  );
}

function ReceiptBody({ t }: { t: Target }) {
  const [view, setView] = useState<"main" | "twin">("main");
  const scroller = useRef<HTMLDivElement>(null);
  const q = useQuery({
    queryKey: ["receipt", t.record_id, t.field, t.col],
    queryFn: () => api<ReceiptData>(`/api/receipt/${t.record_id}?${new URLSearchParams({ ...(t.field ? { field: t.field } : {}), ...(t.col ? { col: t.col } : {}) })}`),
  });
  useEffect(() => {
    const box = scroller.current, hit = box?.querySelector<HTMLElement>("[data-cited]");
    if (box && hit) box.scrollLeft = Math.max(0, hit.offsetLeft - box.clientWidth / 2 + hit.offsetWidth / 2);
  }, [q.data, view]);
  if (q.isLoading) return <div className="space-y-3"><Skeleton className="h-20" /><Skeleton className="h-64" /></div>;
  if (!q.data) return <p className="text-ink-2">This row is no longer in the store.</p>;
  const d = q.data;
  const colIdx = d.col ? d.col.split("").reduce((a, c) => a * 26 + c.charCodeAt(0) - 64, 0) - 1 : -1;
  const cited = d.rows.find((r) => r.cited);
  const value = cited && colIdx >= 0 ? cited.cells[colIdx] : null;
  const showTwin = view === "twin" && d.twin;
  const headers = showTwin ? d.twin!.headers : d.headers;
  const rows = showTwin ? [{ row: d.twin!.row, cells: d.twin!.cells, cited: true }] : d.rows;
  const twinCol = showTwin && d.field ? d.twin!.headers.findIndex((h) => h === d.headers[colIdx]) : colIdx;
  const markCol = showTwin ? twinCol : colIdx;

  return (
    <div className="space-y-5">
      <div className="rounded-[22px] bg-mint p-4 text-mint-ink">
        <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
          {t.label && <span className="text-[15px] font-semibold">{t.label}</span>}
          {value !== null && <span className="num rounded-md bg-mark px-1.5 text-[17px] font-bold text-ink">“{value || "blank"}”</span>}
        </div>
        <p className="mt-1.5 text-[14px] leading-snug">
          Typed by the trainer in <b>{d.file}</b>, sheet <b>{d.sheet}</b>, cell <b className="num">{d.col ?? ""}{d.row}</b>.
        </p>
      </div>

      <dl className="grid grid-cols-2 gap-3 text-[13px] sm:grid-cols-4">
        <Fact label="Round" value={d.round.label} />
        <Fact label="Tested" value={fmtDate(d.round.test_date, { day: "numeric", month: "short", year: "numeric" })} />
        <Fact label="Uploaded" value={fmtDate(d.uploaded_at.slice(0, 10), { day: "numeric", month: "short", year: "numeric" })} />
        <Fact label="File version" value={<span className="inline-flex items-center gap-1"><Fingerprint className="size-3.5" />{d.sha256.slice(0, 10)}</span>} mono />
      </dl>

      {d.twin && (
        <div className="flex items-center gap-3">
          <Layers className="size-4 text-ink-3" />
          <Segmented size="sm" value={view} onChange={setView} options={[{ value: "main", label: d.sheet }, { value: "twin", label: d.twin.sheet }]} />
        </div>
      )}

      <div ref={scroller} className="overflow-x-auto rounded-[18px] border border-line">
        <table className="num w-max min-w-full border-collapse text-[13px]">
          <thead>
            <tr className="bg-card-2 text-ink-3">
              <th className="sticky left-0 z-10 w-10 bg-card-2 px-2 py-1.5 text-right font-medium" />
              {headers.map((_, i) => (
                <th key={i} className={cx("min-w-[64px] px-2 py-1.5 text-left font-medium", i === markCol && "bg-mark/60 text-ink")}>{letter(i)}</th>
              ))}
            </tr>
            <tr className="border-b border-line">
              <th className="sticky left-0 z-10 bg-card px-2 py-2 text-right font-medium text-ink-3">{d.header_row}</th>
              {headers.map((h, i) => (
                <th key={i} className={cx("max-w-[180px] px-2 py-2 text-left align-bottom text-[12px] leading-tight font-semibold text-ink-2", i === markCol && "bg-mark/40 text-ink")}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {!showTwin && d.rows[0]?.row > d.header_row + 1 && (
              <tr><td className="sticky left-0 bg-card px-2 text-right text-ink-3">⋮</td><td colSpan={headers.length} /></tr>
            )}
            {rows.map((r) => (
              <tr key={r.row} className={cx("border-b border-line last:border-0", r.cited ? "bg-accent-soft" : "text-ink-3")}>
                <td className={cx("sticky left-0 z-10 px-2 py-2 text-right font-medium", r.cited ? "bg-accent-soft text-accent-ink" : "bg-card")}>{r.row}</td>
                {headers.map((_, i) => {
                  const hit = r.cited && i === markCol;
                  return (
                    <td key={i} data-cited={hit || undefined} className={cx("max-w-[200px] truncate px-2 py-2", r.cited && "text-ink", hit && "relative font-bold")}>
                      {hit ? <span className="rounded-[5px] bg-mark px-1.5 py-0.5 ring-2 ring-accent">{r.cells[i] || "blank"}</span> : r.cells[i]}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-[13px] text-ink-2">
        Shown exactly as typed, neighbouring rows included. The stored file is never edited; corrections live as your decisions in the Inbox.
      </p>
    </div>
  );
}

function Fact({ label, value, mono }: { label: string; value: ReactNode; mono?: boolean }) {
  return (
    <div className="rounded-2xl bg-card-2 px-3 py-2.5">
      <dt className="text-[12px] text-ink-3">{label}</dt>
      <dd className={cx("mt-0.5 font-semibold text-ink", mono && "num")}>{value}</dd>
    </div>
  );
}

/** A tappable value that opens its cell. */
export function CellLink({ cite, label, children, className }: { cite: Cite | undefined; label?: string; children: ReactNode; className?: string }) {
  const open = useReceipt();
  if (!cite) return <span className={className}>{children}</span>;
  return (
    <button
      type="button"
      onClick={(e) => { e.stopPropagation(); e.preventDefault(); open({ record_id: cite.record_id, col: cite.cell.replace(/\d+/g, ""), label }); }}
      title={`${cite.file} › ${cite.sheet} › ${cite.cell}`}
      className={cx("group/cell inline-flex items-center gap-1 rounded-lg px-1 -mx-1 underline decoration-line-2 decoration-dotted underline-offset-4 transition-colors hover:bg-mark/50 hover:decoration-transparent", className)}
    >
      {children}
      <span className="num rounded-md bg-card-2 px-1 text-[10.5px] font-semibold text-ink-3 no-underline group-hover/cell:bg-card">{cite.cell}</span>
    </button>
  );
}

