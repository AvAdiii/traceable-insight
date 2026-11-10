// Ask routing chain: on-device model (WebLLM) -> laptop model (Ollama) -> server rules.
// The model only turns a question into a structured query. It never sees children's data.
import type { MLCEngineInterface } from "@mlc-ai/web-llm";
import { api } from "./api";

export const MODELS = [
  { id: "Qwen2.5-1.5B-Instruct-q4f16_1-MLC", label: "Balanced", size: "≈1 GB download · 1.6 GB GPU memory", note: "Best for laptops and recent phones" },
  { id: "Qwen2.5-0.5B-Instruct-q4f16_1-MLC", label: "Lite", size: "≈400 MB download · 0.9 GB GPU memory", note: "For older phones; less accurate" },
  { id: "Qwen3-1.7B-q4f16_1-MLC", label: "Best", size: "≈1.2 GB download · 2 GB GPU memory", note: "Most accurate on hard questions" },
] as const;
/** Preferred laptop model; any installed Qwen model is used if this one is missing. */
export const OLLAMA_MODEL = "qwen2.5:3b";
let ollamaModel: string | null = null;
export const ollamaModelName = () => ollamaModel ?? OLLAMA_MODEL;
const OLLAMA_URL = "http://localhost:11434";
const PREF = "ti.model";

export type EngineState =
  | { status: "unsupported"; reason: string }
  | { status: "idle"; cached: boolean }
  | { status: "loading"; progress: number; text: string }
  | { status: "ready"; model: string }
  | { status: "error"; message: string };

type Listener = (s: EngineState) => void;
let engine: MLCEngineInterface | null = null;
let state: EngineState = { status: "idle", cached: false };
const listeners = new Set<Listener>();
let promptCache: { system: string; schema: object; examples: { q: string; a: object }[] } | null = null;

function set(s: EngineState) { state = s; listeners.forEach((l) => l(s)); }
export function subscribe(l: Listener) { listeners.add(l); l(state); return () => { listeners.delete(l); }; }
export function getState() { return state; }

export function preferredModel(): string {
  try { return localStorage.getItem(PREF) || MODELS[0].id; } catch { return MODELS[0].id; }
}
export function setPreferredModel(id: string) { try { localStorage.setItem(PREF, id); } catch { /* ignore */ } }

export async function probe(): Promise<void> {
  const gpu = (navigator as Navigator & { gpu?: { requestAdapter(): Promise<unknown> } }).gpu;
  if (!gpu) return set({ status: "unsupported", reason: "This browser has no WebGPU. Ask uses the laptop model or rules instead." });
  try {
    const adapter = await gpu.requestAdapter();
    if (!adapter) return set({ status: "unsupported", reason: "No GPU adapter available. Ask uses rules instead." });
  } catch { return set({ status: "unsupported", reason: "WebGPU failed to start." }); }
  if (engine) return;
  try {
    const { hasModelInCache } = await import("@mlc-ai/web-llm");
    const cached = await hasModelInCache(preferredModel());
    set({ status: "idle", cached });
    if (cached) void load();
  } catch { set({ status: "idle", cached: false }); }
}

export async function load(model = preferredModel()): Promise<void> {
  if (state.status === "loading") return;
  setPreferredModel(model);
  set({ status: "loading", progress: 0, text: "Starting" });
  try {
    const { CreateWebWorkerMLCEngine } = await import("@mlc-ai/web-llm");
    if (engine) { await engine.unload(); engine = null; }
    engine = await CreateWebWorkerMLCEngine(
      new Worker(new URL("../llm.worker.ts", import.meta.url), { type: "module" }),
      model,
      { initProgressCallback: (r) => set({ status: "loading", progress: r.progress, text: r.text }) },
    );
    set({ status: "ready", model });
  } catch (e) {
    engine = null;
    set({ status: "error", message: e instanceof Error ? e.message : String(e) });
  }
}

export async function remove(model = preferredModel()) {
  const { deleteModelAllInfoInCache } = await import("@mlc-ai/web-llm");
  if (engine) { await engine.unload(); engine = null; }
  await deleteModelAllInfoInCache(model);
  set({ status: "idle", cached: false });
}

async function prompt() {
  promptCache ??= await api("/api/ask/prompt");
  return promptCache!;
}

function messages(p: Awaited<ReturnType<typeof prompt>>, question: string, model: string) {
  const think = model.startsWith("Qwen3") ? " /no_think" : "";
  const shots = p.examples.flatMap((e) => [
    { role: "user" as const, content: e.q },
    { role: "assistant" as const, content: JSON.stringify(e.a) },
  ]);
  return [{ role: "system" as const, content: p.system }, ...shots, { role: "user" as const, content: question + think }];
}

function parseJson(text: string): Record<string, unknown> | null {
  const m = text.replace(/<think>[\s\S]*?<\/think>/g, "").match(/\{[\s\S]*\}/);
  if (!m) return null;
  try { const o = JSON.parse(m[0]); return o && typeof o === "object" ? o : null; } catch { return null; }
}

async function viaWebLLM(question: string) {
  if (!engine || state.status !== "ready") return null;
  const p = await prompt();
  const r = await engine.chat.completions.create({
    messages: messages(p, question, state.model), temperature: 0, max_tokens: 200,
    response_format: { type: "json_object", schema: JSON.stringify(p.schema) },
  });
  return parseJson(r.choices[0]?.message?.content ?? "");
}

let ollamaOk: boolean | null = null;
export async function ollamaAvailable(): Promise<boolean> {
  if (ollamaOk) return true;          // re-probe on later questions if Ollama was down
  try {
    const ctl = new AbortController();
    const t = setTimeout(() => ctl.abort(), 1500);
    const r = await fetch(`${OLLAMA_URL}/api/tags`, { signal: ctl.signal });
    clearTimeout(t);
    const j = await r.json();
    const names: string[] = (j.models ?? []).map((m: { name: string }) => m.name);
    ollamaModel = names.find((n) => n === OLLAMA_MODEL || n === `${OLLAMA_MODEL}:latest`)
      ?? names.find((n) => /^qwen[\d.]+:/i.test(n))      // official tags, e.g. qwen3.5:9b-q4_K_M
      ?? names.find((n) => /^qwen/i.test(n)) ?? names[0] ?? null;
    ollamaOk = !!ollamaModel;
  } catch { ollamaOk = false; }
  return ollamaOk ?? false;
}

async function viaOllama(question: string) {
  if (!(await ollamaAvailable())) return null;
  const p = await prompt();
  const model = ollamaModelName();
  const r = await fetch(`${OLLAMA_URL}/api/chat`, {
    method: "POST",
    // think:false keeps reasoning models (Qwen3/3.5) answering directly; keep_alive avoids reloads.
    body: JSON.stringify({ model, messages: messages(p, question, "qwen2"), stream: false, think: false,
      keep_alive: "30m", format: p.schema, options: { temperature: 0, seed: 7 } }),
  });
  if (!r.ok) return null;
  const j = await r.json();
  return parseJson(j.message?.content ?? "");
}

export type Routed = { spec: Record<string, unknown>; routed_by: string };

export async function route(question: string): Promise<Routed> {
  try {
    const s = await viaWebLLM(question);
    if (s?.action) return { spec: s, routed_by: `On-device · ${MODELS.find((m) => m.id === preferredModel())?.label ?? "model"}` };
  } catch { /* fall through */ }
  try {
    const s = await viaOllama(question);
    if (s?.action) return { spec: s, routed_by: `Laptop · ${ollamaModelName()}` };
  } catch { /* fall through */ }
  const spec = await api("/api/ask/parse", { method: "POST", json: { question } });
  return { spec, routed_by: "Rules" };
}
