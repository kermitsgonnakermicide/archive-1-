import React, { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { toast } from "sonner";
import { useApp } from "../context/AppContext";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";

const LOGO_URL = "https://customer-assets.emergentagent.com/job_scale-talent-network/artifacts/xgqkusx7_Untitled%20design.jpg";

export default function AuthPage({ mode = "login" }) {
  const { login, signup } = useApp();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ email: "", password: "", name: "" });
  const [busy, setBusy] = useState(false);
  const isSignup = mode === "signup";

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const user = isSignup
        ? await signup(form.email, form.password, form.name)
        : await login(form.email, form.password);
      toast.success(isSignup ? "Account created." : "Welcome back.");
      const dest = location.state?.from || (user.role === "admin" ? "/admin" : "/");
      navigate(dest);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Something went wrong.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen hero-bg flex items-center justify-center py-20 px-6" data-testid="auth-page">
      <div className="w-full max-w-md bg-white p-8 md:p-10 relative">
        <div className="absolute -top-2 -left-2 -right-2 h-1 bg-[var(--scale-gold)]" />
        <Link to="/" className="flex items-center justify-center mb-6">
          <img src={LOGO_URL} alt="SCALE" className="h-14 w-auto" />
        </Link>
        <h1 className="font-serif font-black text-3xl text-center mb-1">
          {isSignup ? "Create your account" : "Welcome back"}
        </h1>
        <p className="text-sm text-center text-black/60 mb-6">
          {isSignup ? "Join India's serious platform for high school business talent." : "Log in to continue."}
        </p>
        <form onSubmit={submit} className="grid gap-4" data-testid="auth-form">
          {isSignup && (
            <div>
              <Label className="text-xs uppercase tracking-wider font-semibold text-black/70">Full name</Label>
              <Input value={form.name} onChange={set("name")} data-testid="auth-name" className="mt-1.5" />
            </div>
          )}
          <div>
            <Label className="text-xs uppercase tracking-wider font-semibold text-black/70">Email</Label>
            <Input type="email" value={form.email} onChange={set("email")} required data-testid="auth-email" className="mt-1.5" />
          </div>
          <div>
            <Label className="text-xs uppercase tracking-wider font-semibold text-black/70">Password</Label>
            <Input type="password" value={form.password} onChange={set("password")} required data-testid="auth-password" className="mt-1.5" />
          </div>
          <button disabled={busy} className="btn-crimson justify-center" data-testid="auth-submit">
            {busy ? "Please wait..." : isSignup ? "Create Account" : "Log In"}
          </button>
        </form>
        <div className="text-center text-sm text-black/60 mt-6">
          {isSignup ? (
            <>Already have an account? <Link to="/login" className="text-[var(--scale-crimson)] font-semibold">Log in</Link></>
          ) : (
            <>New here? <Link to="/signup" className="text-[var(--scale-crimson)] font-semibold">Create an account</Link></>
          )}
        </div>
        <div className="text-center mt-4">
          <Link to="/" className="text-xs uppercase tracking-[0.28em] text-black/50 hover:text-black">← Back to site</Link>
        </div>
      </div>
    </div>
  );
}
