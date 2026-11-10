import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type Meta } from "./api";

export const useMeta = () => useQuery({ queryKey: ["meta"], queryFn: () => api<Meta>("/api/meta"), staleTime: 60_000 });

export function useSchoolName() {
  const m = useMeta();
  return (id: string | null | undefined) => m.data?.schools.find((s) => s.id === id)?.short ?? "";
}

/** Mutation that refreshes every derived view (decisions re-run the pipeline). */
export function useAct<TVars, TRes = unknown>(fn: (v: TVars) => Promise<TRes>, onDone?: (r: TRes, v: TVars) => void) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: (r, v) => { qc.invalidateQueries(); onDone?.(r, v); },
  });
}
