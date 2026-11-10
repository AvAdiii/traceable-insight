import { ArrowRight, ClipboardList, Lock, Mail, UserCog, Whistle } from "lucide-react";
import { useState } from "react";
import { Logo } from "../components/Shell";
import { Button, Illus, cx } from "../components/ui";
import { useAuth } from "../lib/auth";

const DEMO = [
  { email: "manager@champion.demo", label: "Programme manager", icon: UserCog },
  { email: "supervisor@champion.demo", label: "Supervisor PT", icon: ClipboardList },
  { email: "trainer@champion.demo", label: "PT trainer", icon: Whistle },
];

export default function Login() {
  const { signIn } = useAuth();
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const go = async (e?: React.FormEvent, em = email, p = pw) => {
    e?.preventDefault();
    setBusy(true); setErr("");
    try { await signIn(em, p); } catch (x) { setErr(x instanceof Error ? x.message : "Could not sign in"); } finally { setBusy(false); }
  };
  return (
    <div className="grid min-h-dvh lg:grid-cols-[1.05fr_1fr]">
      <div className="relative hidden overflow-hidden bg-plate p-12 text-plate-ink lg:flex lg:flex-col lg:justify-between">
        <Logo />
        <Illus name="track-and-field" className="mx-auto w-full max-w-[520px]" />
        <div className="max-w-md">
          <h2 className="text-[30px] leading-tight font-extrabold tracking-[-0.025em] text-plate-ink">Every child’s jump, throw and run, traced to the cell it came from.</h2>
          <p className="mt-2 text-[15px] text-plate-ink">Project Champion · Hyderabad Runners Society</p>
        </div>
      </div>

      <div className="flex flex-col justify-center px-5 py-10 sm:px-12">
        <div className="mx-auto w-full max-w-[400px]">
          <div className="mb-10 lg:hidden"><Logo /></div>
          <h1 className="text-[32px] font-extrabold tracking-[-0.03em]">Sign in</h1>
          <p className="mt-1 text-[15px] text-ink-2">Use your programme account.</p>
          <form onSubmit={go} className="mt-7 space-y-3">
            <Field icon={Mail} type="email" value={email} onChange={setEmail} placeholder="Email" autoComplete="email" />
            <Field icon={Lock} type="password" value={pw} onChange={setPw} placeholder="Password" autoComplete="current-password" />
            {err && <p role="alert" className="rounded-2xl bg-rose px-4 py-2.5 text-[14px] font-medium text-rose-ink">{err}</p>}
            <Button type="submit" variant="primary" loading={busy} className="h-12 w-full">Sign in <ArrowRight className="size-4" /></Button>
          </form>
          <div className="mt-9">
            <p className="mb-2.5 text-[13px] font-semibold text-ink-2">Demo workspace (synthetic data) · password “champion”</p>
            <div className="grid grid-cols-3 gap-2">
              {DEMO.map((d) => (
                <button key={d.email} onClick={() => { setEmail(d.email); setPw("champion"); void go(undefined, d.email, "champion"); }}
                  className="flex flex-col items-center gap-2 rounded-[20px] bg-card p-3 text-center text-[12.5px] font-semibold shadow-card transition-transform hover:-translate-y-0.5">
                  <d.icon className="size-6 text-ink-2" strokeWidth={1.8} />{d.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Field({ icon: Icon, value, onChange, ...rest }: { icon: typeof Mail; value: string; onChange: (v: string) => void } & Omit<React.InputHTMLAttributes<HTMLInputElement>, "onChange" | "value">) {
  return (
    <label className={cx("flex h-13 items-center gap-3 rounded-2xl bg-card px-4 shadow-card focus-within:ring-2 focus-within:ring-accent/60")}>
      <Icon className="size-[18px] text-ink-3" />
      <input {...rest} value={value} onChange={(e) => onChange(e.target.value)} required aria-label={rest.placeholder}
        className="h-full min-w-0 flex-1 bg-transparent text-[16px] outline-none placeholder:text-ink-3" />
    </label>
  );
}
