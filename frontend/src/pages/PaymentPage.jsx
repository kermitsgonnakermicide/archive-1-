import React, { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { registrationsApi, paymentsApi } from "../lib/api";
import { toast } from "sonner";
import { LOGO_URL } from "../lib/brand";
import { CreditCard, Smartphone, Loader2 } from "lucide-react";

const CASHFREE_SDK = "https://sdk.cashfree.com/js/v3/cashfree.js";

function loadCashfreeScript() {
  return new Promise((resolve) => {
    if (window.Cashfree) return resolve(true);
    const existing = document.querySelector(`script[src="${CASHFREE_SDK}"]`);
    if (existing) {
      existing.addEventListener("load", () => resolve(!!window.Cashfree));
      existing.addEventListener("error", () => resolve(false));
      return;
    }
    const s = document.createElement("script");
    s.src = CASHFREE_SDK;
    s.async = true;
    s.onload = () => resolve(!!window.Cashfree);
    s.onerror = () => resolve(false);
    document.body.appendChild(s);
  });
}

export default function PaymentPage() {
  const { registrationId } = useParams();
  const navigate = useNavigate();
  const [reg, setReg] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    (async () => {
      try { setReg(await registrationsApi.get(registrationId)); }
      catch { toast.error("Registration not found."); navigate("/"); }
    })();
    loadCashfreeScript();
  }, [registrationId, navigate]);

  const initiate = useCallback(async () => {
    setBusy(true);
    const sdkOk = await loadCashfreeScript();
    if (!sdkOk || !window.Cashfree) {
      toast.error("Payment SDK failed to load. Check your internet and try again.");
      setBusy(false);
      return;
    }
    let order;
    try {
      order = await paymentsApi.createOrder(registrationId);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Could not start payment.");
      setBusy(false);
      return;
    }
    if (!order?.payment_session_id) {
      toast.error("Payment gateway not configured. Please contact support.");
      setBusy(false);
      return;
    }
    try {
      // Cashfree v3 drop-in. Mode = "sandbox" for TEST, "production" for PROD.
      const mode = (order.env || "TEST").toUpperCase() === "PROD" ? "production" : "sandbox";
      const cashfree = window.Cashfree({ mode });
      cashfree.checkout({
        paymentSessionId: order.payment_session_id,
        redirectTarget: "_self",  // redirect back to our return_url
      });
      // On redirect the browser navigates away; no further JS runs here.
    } catch (e) {
      toast.error("Could not open checkout. Please try again.");
      setBusy(false);
    }
  }, [registrationId]);

  if (!reg) return <div className="min-h-screen flex items-center justify-center">Loading…</div>;

  if (reg.payment_status === "paid") {
    return (
      <div className="min-h-screen flex items-center justify-center hero-bg px-6 pt-20">
        <div className="bg-white p-8 max-w-md w-full text-center" data-testid="payment-already-paid">
          <div className="text-5xl mb-3">✓</div>
          <h1 className="font-serif font-black text-3xl mb-2">Payment already complete</h1>
          <p className="text-sm text-black/70 mb-5">Your spot for {reg.event_title} is confirmed.</p>
          <button onClick={() => navigate("/")} className="btn-crimson w-full justify-center">Back to home</button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen hero-bg pt-24 pb-16 flex items-start justify-center px-6" data-testid="payment-page">
      <div className="w-full max-w-lg bg-white">
        <div className="bg-[var(--scale-darkred)] text-white px-6 py-5 flex items-center gap-3">
          <img src={LOGO_URL} alt="" className="h-10 rounded-sm" />
          <div>
            <div className="text-[10px] tracking-[0.3em] uppercase text-[var(--scale-goldlight)] font-bold">Secure Payment</div>
            <div className="font-serif font-bold text-lg">SCALE Event Registration</div>
          </div>
        </div>
        <div className="p-6 md:p-8">
          <div className="mb-6">
            <div className="text-xs uppercase tracking-wider text-black/50">Event</div>
            <div className="font-serif font-bold text-xl">{reg.event_title}</div>
          </div>
          <div className="mb-6 grid grid-cols-2 gap-y-3 gap-x-4 text-sm">
            <Cell k="Student" v={reg.name} />
            <Cell k="Grade" v={reg.grade} />
            <Cell k="School" v={reg.school} />
            <Cell k="Email" v={reg.email} />
          </div>
          <div className="border-t border-b border-black/10 py-4 mb-6 flex items-center justify-between">
            <span className="font-serif text-base">Total payable</span>
            <span className="font-serif font-black text-3xl text-[var(--scale-crimson)]">₹{Math.round(reg.amount_inr || 500)}</span>
          </div>
          <div className="flex items-center gap-3 mb-5 text-xs text-black/60 flex-wrap">
            <span className="flex items-center gap-1"><Smartphone size={14} /> UPI</span>
            <span className="flex items-center gap-1"><CreditCard size={14} /> Cards</span>
            <span>· Netbanking · Wallets</span>
            <span className="ml-auto">Powered by Cashfree</span>
          </div>
          <button
            onClick={initiate}
            disabled={busy}
            className="btn-crimson w-full justify-center"
            data-testid="payment-initiate-btn"
          >
            {busy ? <><Loader2 className="animate-spin" size={14} /> Redirecting…</> : "Pay Securely"}
          </button>
          <p className="text-xs text-black/50 mt-3 text-center">
            You'll be redirected to Cashfree's secure checkout — UPI, cards, netbanking, and wallets supported.
          </p>
        </div>
      </div>
    </div>
  );
}

function Cell({ k, v }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider text-black/50 font-semibold">{k}</div>
      <div className="font-medium">{v}</div>
    </div>
  );
}
