import React, { useEffect, useState, useRef } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { paymentsApi, registrationsApi } from "../lib/api";
import { LOGO_URL } from "../lib/brand";
import { Loader2 } from "lucide-react";

export default function PaymentSuccessPage() {
  const [params] = useSearchParams();
  const sessionId = params.get("session_id");
  const regId = params.get("reg");
  const navigate = useNavigate();
  const [status, setStatus] = useState("checking");
  const [info, setInfo] = useState(null);
  const [eventId, setEventId] = useState(null);
  const attemptsRef = useRef(0);

  useEffect(() => {
    if (!sessionId) { setStatus("error"); return; }
    let cancelled = false;
    // Lookup the event id from the registration so we can deep-link to the hub.
    if (regId) {
      registrationsApi.get(regId).then((r) => !cancelled && setEventId(r?.event_id)).catch(() => {});
    }
    const poll = async () => {
      attemptsRef.current += 1;
      try {
        const res = await paymentsApi.status(sessionId);
        if (cancelled) return;
        setInfo(res);
        if (res.payment_status === "paid") { setStatus("paid"); return; }
        if (res.status === "expired" || res.payment_status === "failed") { setStatus("failed"); return; }
        if (attemptsRef.current >= 8) { setStatus("timeout"); return; }
        setTimeout(poll, 2000);
      } catch {
        if (attemptsRef.current >= 4) { setStatus("confirming"); return; }
        setTimeout(poll, 2500);
      }
    };
    poll();
    return () => { cancelled = true; };
  }, [sessionId, regId]);

  return (
    <div className="min-h-screen hero-bg pt-24 pb-16 flex items-center justify-center px-6" data-testid="payment-success-page">
      <div className="w-full max-w-lg bg-white p-8 md:p-10 text-center">
        <img src={LOGO_URL} alt="SCALE" className="h-14 mx-auto mb-6 rounded-sm" />
        {status === "checking" && (
          <>
            <Loader2 className="animate-spin mx-auto text-[var(--scale-crimson)]" size={32} />
            <h1 className="font-serif font-black text-2xl mt-4">Confirming your payment…</h1>
            <p className="text-sm text-black/60 mt-2">This usually takes a few seconds.</p>
          </>
        )}
        {status === "paid" && (
          <>
            <div className="text-5xl text-[var(--scale-crimson)] mb-2">✓</div>
            <h1 className="font-serif font-black text-3xl">Payment Confirmed</h1>
            <p className="text-base text-black/70 mt-3">
              Your spot is locked. A receipt has been emailed to you and your parent.
            </p>
            {info?.amount && (
              <div className="mt-5 inline-block bg-[var(--scale-cream)] border-l-4 border-[var(--scale-gold)] px-5 py-3 text-left">
                <div className="text-xs uppercase tracking-wider text-black/50">Amount paid</div>
                <div className="font-serif font-black text-2xl">₹{Math.round(info.amount)}</div>
              </div>
            )}
            {eventId && regId ? (
              <button
                onClick={() => navigate(`/events/${eventId}/registered?reg=${regId}`)}
                className="btn-crimson mt-6 w-full justify-center"
                data-testid="success-goto-hub-btn"
              >
                Go to Event Hub →
              </button>
            ) : (
              <button onClick={() => navigate("/")} className="btn-crimson mt-6 w-full justify-center" data-testid="success-home-btn">
                Back to SCALE Home
              </button>
            )}
          </>
        )}
        {status === "confirming" && (
          <>
            <div className="text-5xl text-[var(--scale-gold)] mb-2">✓</div>
            <h1 className="font-serif font-black text-2xl">Payment received</h1>
            <p className="text-sm text-black/70 mt-3">
              Your payment has been received. A confirmation email will arrive within a few minutes as we finalise your registration.
            </p>
            <button onClick={() => navigate("/")} className="btn-crimson mt-6 w-full justify-center">Back to SCALE Home</button>
          </>
        )}
        {(status === "failed" || status === "error" || status === "timeout") && (
          <>
            <div className="text-5xl text-[var(--scale-crimson)] mb-2">!</div>
            <h1 className="font-serif font-black text-2xl">Payment {status === "timeout" ? "still processing" : "issue"}</h1>
            <p className="text-sm text-black/70 mt-2">
              {status === "timeout"
                ? "It's taking longer than expected. Check your email shortly — if you've been charged, your registration will be confirmed."
                : "Something went wrong. Please try again or contact us if you've been charged."}
            </p>
            <button onClick={() => navigate("/")} className="btn-outline-dark mt-5 w-full justify-center">Back to home</button>
          </>
        )}
      </div>
    </div>
  );
}
