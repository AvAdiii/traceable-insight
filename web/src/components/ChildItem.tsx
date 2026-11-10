import { ChevronRight } from "lucide-react";
import { Link } from "react-router-dom";
import type { FlagKind } from "../lib/api";
import { Avatar, FlagChip, cx } from "./ui";

export function ChildItem({ id, name, sub, right, flags, className }: { id: string; name: string; sub: string; right?: React.ReactNode; flags?: FlagKind[]; className?: string }) {
  return (
    <Link to={`/children/${id}`} className={cx("group flex min-h-14 items-center gap-3 rounded-2xl px-2 py-2 transition-colors hover:bg-card-2", className)}>
      <Avatar name={name} />
      <div className="min-w-0 flex-1">
        <div className="truncate text-[15px] font-semibold">{name}</div>
        <div className="truncate text-[13px] text-ink-2">{sub}</div>
      </div>
      {flags && flags.length > 0 && <div className="hidden gap-1 sm:flex">{[...new Set(flags)].slice(0, 3).map((f) => <FlagChip key={f} kind={f} compact />)}</div>}
      {right}
      <ChevronRight className="size-4 shrink-0 text-ink-3 transition-transform group-hover:translate-x-0.5" />
    </Link>
  );
}
