// Thin typed client for the FastAPI read/write layer.

const BASE = import.meta.env.VITE_API_URL ?? "";
const TOKEN_KEY = "ti.token";

export function getToken(): string | null {
  try { return localStorage.getItem(TOKEN_KEY); } catch { return null; }
}
export function setToken(t: string | null) {
  try { t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY); } catch { /* private mode */ }
}

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

export async function api<T = any>(path: string, init: RequestInit & { json?: unknown } = {}): Promise<T> {
  const headers: Record<string, string> = { ...(init.headers as Record<string, string>) };
  const tok = getToken();
  if (tok) headers.Authorization = `Bearer ${tok}`;
  let body = init.body;
  if (init.json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(init.json);
  }
  const res = await fetch(BASE + path, { ...init, headers, body });
  if (res.status === 401 && !path.startsWith("/api/auth")) {
    setToken(null);
    window.dispatchEvent(new Event("ti:signed-out"));
  }
  if (!res.ok) {
    let msg = res.statusText;
    try { const j = await res.json(); msg = typeof j.detail === "string" ? j.detail : msg; } catch { /* not json */ }
    throw new ApiError(res.status, msg);
  }
  const ct = res.headers.get("content-type") ?? "";
  return (ct.includes("json") ? res.json() : res.text()) as Promise<T>;
}

export function qs(params: Record<string, unknown>): string {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== null && v !== "") p.set(k, String(v));
  const s = p.toString();
  return s ? `?${s}` : "";
}

// ---- types (mirror ti.queries) ----
export type User = { id: number; name: string; email: string; role: "manager" | "supervisor" | "trainer" };
export type SchoolBrief = { id: string; name: string; short: string; area: string; hue: number; trainer: User | null; supervisor: User | null };
export type Round = { id: number; label: string; kind: string; test_date: string };
export type Test = { key: TestKey; label: string; full: string; unit: string; skill: string; lower_is_better: boolean };
export type TestKey = "jump" | "shuttle" | "ball" | "relay";
export type Discipline = { key: string; label: string; examples: string; weights: Record<string, number> };
export type FlagKind = "top" | "improved" | "push" | "declining" | "missing";
export type Meta = { user: User; schools: SchoolBrief[]; rounds: Round[]; tests: Test[]; disciplines: Discipline[]; flags: { key: FlagKind; label: string; short: string }[]; coaches: User[] };

export type Cite = { record_id: number; file: string; sheet: string; cell: string; row?: number; raw: string };
export type ChildRow = {
  id: string; name: string; gender: string; klass: string; age: number | null; school_id: string; school: string;
  composite: number | null; tests: Partial<Record<TestKey, { value: number | null; percentile: number | null; status: string }>>;
  flags: { kind: FlagKind; text: string }[]; trend: number | null; cite?: Cite;
};
export type TestCell = { value: number | null; raw: string; unit: string; status: string; note: string; percentile: number | null; pool: string; cite: Cite };
export type ChildRound = Round & { composite: number | null; age: number | null; klass: string; tests: Record<string, TestCell> };
export type ChildDetail = {
  id: string; name: string; aliases: string[]; parent: string; dob: string | null; gender: string; klass: string; school: SchoolBrief;
  rounds: ChildRound[]; flags: { kind: FlagKind; text: string; evidence: number[] }[];
  achievements: { event: string; event_id: number; date: string; level: string; item: string; position: number | null; mark: string; note: string }[];
  selections: { event: string; event_id: number; date: string; item: string; status: string }[];
  issues: Issue[]; progress: Record<string, { from: number; to: number; delta: number; pct: number; better: boolean }>;
};
export type Issue = {
  key: string; kind: string; severity: "high" | "medium" | "low"; school_id: string | null; upload_id: number | null; child_id: string | null;
  field: string; title: string; detail: string; record_ids: number[]; count: number; resolved: boolean; resolution: Record<string, unknown>;
  options: { id: string; label: string; input?: string; payload: Record<string, unknown>; score?: number }[];
};
export type EventBrief = {
  id: number; title: string; kind: string; level: string; start_date: string; end_date: string | null; start_time: string; venue: string; notes: string;
  school_ids: string[]; items: number; slots: number; picked: number; todos: number; todos_done: number;
};
export type Todo = { id: number; event_id: number | null; text: string; done: boolean; due_date: string | null };
export type Selection = { child_id: string; name: string; klass: string; gender: string; school_id: string; status: string; rank: number; summary: string; result: { position: number | null; mark: string; note: string } | null };
export type EventItem = { id: number; name: string; discipline: string; gender: string; age_min: number | null; age_max: number | null; slots: number; reserves: number; selections: Selection[] };
export type EventDetail = EventBrief & { items_detail: EventItem[]; todo_list: Todo[] };
export type Reason = { field: TestKey; label: string; value: number; text: string; percentile: number; pool: string; weight: number; cite: Cite & { measurement_id: number } };
export type Candidate = {
  child_id: string; name: string; gender: string; klass: string; school_id: string; school: string; age: number | null; round: string;
  score: number; reasons: Reason[]; trend: number | null; missing: string[]; summary: string; composite: number | null; chosen?: string | null; also?: string[];
};
export type Suggestion = {
  selected: Candidate[]; reserves: Candidate[]; more: Candidate[]; held: (Omit<Candidate, "score" | "reasons"> & { why: string })[];
  pool: number; weights: Record<string, number>; discipline: Discipline; item: Omit<EventItem, "selections">;
};
