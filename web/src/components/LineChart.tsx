import { motion } from "motion/react";
import { useEffect, useMemo, useRef, useState } from "react";
import { cx } from "./ui";

export type Series = { id: string; label: string; values: (number | null)[] };

/** Monotone cubic path through points (no overshoot between rounds). */
function smooth(pts: [number, number][]): string {
  if (pts.length < 2) return pts.length ? `M${pts[0][0]},${pts[0][1]}` : "";
  const n = pts.length;
  const dx = pts.slice(1).map((p, i) => p[0] - pts[i][0]);
  const m = pts.slice(1).map((p, i) => (p[1] - pts[i][1]) / dx[i]);
  const t = pts.map((_, i) => (i === 0 ? m[0] : i === n - 1 ? m[n - 2] : m[i - 1] * m[i] <= 0 ? 0 : (m[i - 1] + m[i]) / 2));
  let d = `M${pts[0][0]},${pts[0][1]}`;
  for (let i = 0; i < n - 1; i++) {
    const h = dx[i] / 3;
    d += ` C${pts[i][0] + h},${pts[i][1] + t[i] * h} ${pts[i + 1][0] - h},${pts[i + 1][1] - t[i + 1] * h} ${pts[i + 1][0]},${pts[i + 1][1]}`;
  }
  return d;
}

export function LineChart({
  xLabels, main, context = [], format, height = 260, lowerIsBetter, mainLabel = "Programme average", unitNote,
}: {
  xLabels: string[]; main: (number | null)[]; context?: Series[]; format: (v: number) => string; height?: number;
  lowerIsBetter?: boolean; mainLabel?: string; unitNote?: string;
}) {
  const box = useRef<SVGSVGElement>(null);
  const [hover, setHover] = useState<number | null>(null);
  const [focusId, setFocusId] = useState<string | null>(null);
  const wrap = useRef<HTMLDivElement>(null);
  const [W, setW] = useState(640);
  useEffect(() => {
    const el = wrap.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => setW(Math.max(260, Math.round(e.contentRect.width))));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  const H = height, L = 52, R = 18, T = 18, B = 34;

  const all = [...main, ...context.flatMap((s) => s.values)].filter((v): v is number => v !== null);
  const [lo, hi] = useMemo(() => {
    if (!all.length) return [0, 1];
    const mn = Math.min(...all), mx = Math.max(...all);
    const pad = (mx - mn) * 0.15 || mx * 0.05 || 1;
    return [mn - pad, mx + pad];
  }, [all.join()]); // eslint-disable-line react-hooks/exhaustive-deps
  const x = (i: number) => L + (xLabels.length === 1 ? (W - L - R) / 2 : (i * (W - L - R)) / (xLabels.length - 1));
  const y = (v: number) => T + (1 - (v - lo) / (hi - lo)) * (H - T - B);
  const ticks = Array.from({ length: 4 }, (_, i) => lo + ((i + 0.5) * (hi - lo)) / 4);
  const pts = (vals: (number | null)[]) => vals.flatMap((v, i) => (v === null ? [] : [[x(i), y(v)] as [number, number]]));
  const mainPts = pts(main);

  const onMove = (e: React.PointerEvent) => {
    const r = box.current!.getBoundingClientRect();
    const px = ((e.clientX - r.left) / r.width) * W;
    let best = 0;
    xLabels.forEach((_, i) => { if (Math.abs(x(i) - px) < Math.abs(x(best) - px)) best = i; });
    setHover(best);
  };

  const tip = hover !== null ? [...context]
    .map((s) => ({ ...s, v: s.values[hover] }))
    .filter((s) => s.v !== null)
    .sort((a, b) => (lowerIsBetter ? a.v! - b.v! : b.v! - a.v!)) : [];

  return (
    <div ref={wrap} className="relative">
      <svg ref={box} viewBox={`0 0 ${W} ${H}`} width={W} height={H} className="block w-full touch-none select-none" role="img"
        aria-label={`${mainLabel}: ${xLabels.map((l, i) => `${l} ${main[i] !== null ? format(main[i]!) : "no data"}`).join(", ")}`}
        onPointerMove={onMove} onPointerLeave={() => { setHover(null); setFocusId(null); }}>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={L} x2={W - R} y1={y(t)} y2={y(t)} stroke="var(--line)" strokeDasharray="2 5" />
            <text x={L - 10} y={y(t)} dy="0.32em" textAnchor="end" className="num fill-ink-3 text-[11px]">{format(t)}</text>
          </g>
        ))}
        {xLabels.map((l, i) => (
          <text key={l} x={x(i)} y={H - 10} textAnchor={xLabels.length > 1 && i === 0 ? "start" : xLabels.length > 1 && i === xLabels.length - 1 ? "end" : "middle"} dx={xLabels.length > 1 && i === 0 ? -6 : xLabels.length > 1 && i === xLabels.length - 1 ? 6 : 0} className={cx("text-[12px] font-medium", hover === i ? "fill-ink" : "fill-ink-3")}>{l}</text>
        ))}
        {context.map((s) => {
          const on = focusId === s.id;
          return (
            <path key={s.id} d={smooth(pts(s.values))} fill="none" stroke={on ? "var(--ink)" : "var(--chart-context)"} strokeWidth={on ? 2 : 1.25}
              strokeOpacity={focusId && !on ? 0.35 : 0.85} onPointerEnter={() => setFocusId(s.id)} className="cursor-pointer transition-[stroke,opacity]" />
          );
        })}
        <motion.path d={smooth(mainPts)} fill="none" stroke="var(--accent)" strokeWidth={2.5} strokeLinecap="round"
          initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }} />
        {mainPts.map(([px, py], i) => (
          <circle key={i} cx={px} cy={py} r={hover === i ? 7 : 5} fill="var(--card)" stroke="var(--accent)" strokeWidth={3} className="transition-[r]" />
        ))}
        {hover !== null && <line x1={x(hover)} x2={x(hover)} y1={T} y2={H - B} stroke="var(--ink)" strokeOpacity={0.18} />}
        {focusId && (() => {
          const s = context.find((c) => c.id === focusId)!;
          const last = s.values.map((v, i) => [v, i] as const).filter(([v]) => v !== null).pop();
          return last ? <text x={x(last[1]) - 8} y={y(last[0]!) - 10} textAnchor="end" className="fill-ink text-[12px] font-semibold">{s.label}</text> : null;
        })()}
      </svg>

      {hover !== null && (
        <div className="pointer-events-none absolute top-2 z-10 w-56 rounded-2xl bg-invert p-3 text-[12.5px] text-invert-ink shadow-lift"
          style={{ left: `clamp(0px, calc(${(x(hover) / W) * 100}% - 112px), calc(100% - 224px))` }}>
          <div className="mb-1.5 flex items-baseline justify-between gap-2">
            <span className="font-semibold">{xLabels[hover]}</span>
            <span className="num font-bold">{main[hover] !== null ? format(main[hover]!) : "—"}</span>
          </div>
          <div className="mb-1 text-[11px] opacity-70">{mainLabel}{unitNote ? ` · ${unitNote}` : ""}</div>
          <div className="space-y-0.5">
            {tip.slice(0, 8).map((s) => (
              <div key={s.id} className={cx("flex justify-between gap-2", focusId === s.id ? "font-bold" : "opacity-85")}>
                <span className="truncate">{s.label}</span><span className="num">{format(s.v!)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
