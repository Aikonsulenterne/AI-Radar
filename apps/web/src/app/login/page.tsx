"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { getSupabaseBrowserClient } from "../../lib/supabase/client";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const supabase = getSupabaseBrowserClient();

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!supabase) return;
    setError(null);
    setBusy(true);
    const { error: signInError } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    setBusy(false);
    if (signInError) {
      setError("Login mislykkedes. Kontrollér e-mail og adgangskode.");
      return;
    }
    router.push("/");
    router.refresh();
  }

  if (!supabase) {
    return (
      <>
        <h1>Log ind</h1>
        <div className="alert-error" role="alert">
          Login er ikke konfigureret i dette miljø
          (NEXT_PUBLIC_SUPABASE_URL/ANON_KEY mangler). I lokal udvikling
          kører API&#8217;et med dev-adgang uden login.
        </div>
      </>
    );
  }

  return (
    <>
      <h1>Log ind</h1>
      <p className="page-lead">
        AI Radar er internt. Log ind med din OK-/projektkonto — roller
        (Reader, Reviewer, Admin) styres centralt.
      </p>
      <form className="card form-grid login-form" onSubmit={handleSubmit}>
        <div className="field">
          <label htmlFor="login-email">E-mail</label>
          <input
            id="login-email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>
        <div className="field">
          <label htmlFor="login-password">Adgangskode</label>
          <input
            id="login-password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>
        {error ? (
          <p className="alert-error" role="alert">
            {error}
          </p>
        ) : null}
        <div>
          <button type="submit" className="btn" disabled={busy}>
            {busy ? "Logger ind…" : "Log ind"}
          </button>
        </div>
      </form>
    </>
  );
}
