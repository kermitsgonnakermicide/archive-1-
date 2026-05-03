import React, { useEffect, useState, useRef } from "react";
import { useParams, useSearchParams, useNavigate, Link } from "react-router-dom";
import { eventsApi, formsApi, uploadsApi } from "../lib/api";
import { toast } from "sonner";
import { Input } from "../components/ui/input";
import { Textarea } from "../components/ui/textarea";
import { Label } from "../components/ui/label";
import { ArrowLeft, Upload, FileCheck2, X, Loader2 } from "lucide-react";

export default function EventScholarshipPage() {
  const { id } = useParams();
  const [params] = useSearchParams();
  const regId = params.get("reg");
  const navigate = useNavigate();
  const [event, setEvent] = useState(null);
  const [form, setForm] = useState({
    name: "", school: "", grade: "", email: "", phone: "",
    parent_name: "", parent_email: "",
    financial_proof: "", why_participate: "",
  });
  const [proofFile, setProofFile] = useState(null); // { id, original_filename, size }
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => { eventsApi.get(id).then(setEvent).catch(() => navigate("/")); }, [id, navigate]);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const onPickFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) {
      toast.error("File too large (max 10 MB).");
      e.target.value = "";
      return;
    }
    setUploading(true);
    try {
      const res = await uploadsApi.scholarshipProof(file);
      setProofFile(res);
      toast.success("Proof file uploaded.");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Upload failed.");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const clearFile = () => setProofFile(null);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await formsApi.eventScholarship({
        event_id: id,
        ...form,
        proof_file_id: proofFile?.id || null,
      });
      setDone(true);
      toast.success("Scholarship application submitted.");
    } catch { toast.error("Submission failed."); }
    finally { setBusy(false); }
  };

  if (!event) return <div className="min-h-screen flex items-center justify-center">Loading…</div>;

  return (
    <div className="min-h-screen bg-[var(--scale-offwhite)] pt-20" data-testid="event-scholarship-page">
      <section className="dark-red-section py-12">
        <div className="max-container">
          <Link to={`/events/${id}`} className="text-white/70 hover:text-white text-xs uppercase tracking-[0.28em] flex items-center gap-2 mb-4">
            <ArrowLeft size={14} /> Back to {event.title}
          </Link>
          <div className="text-[10px] tracking-[0.28em] uppercase font-bold text-[var(--scale-goldlight)] mb-2">Scholarship Application</div>
          <h1 className="font-serif font-black text-3xl md:text-5xl text-white">
            For {event.title}
          </h1>
          <p className="text-white/80 mt-3 max-w-2xl">
            Financial circumstances should never be a barrier to learning. Every application is reviewed with care, confidentiality, and zero judgement.
          </p>
        </div>
      </section>

      <section className="py-12">
        <div className="max-container max-w-3xl">
          {done ? (
            <div className="bg-white p-8 md:p-10 text-center" data-testid="scholarship-success">
              <div className="text-5xl text-[var(--scale-crimson)] mb-2">✓</div>
              <h2 className="font-serif font-black text-3xl mb-2">Application received</h2>
              <p className="text-black/70">We'll respond within 5–7 business days. A confirmation email has been sent to {form.email}.</p>
              <button onClick={() => navigate("/")} className="btn-crimson mt-5 justify-center">Back to home</button>
            </div>
          ) : (
            <form onSubmit={submit} className="bg-white p-6 md:p-10 grid gap-4" data-testid="scholarship-form">
              {regId && (
                <div className="bg-[var(--scale-cream)] border-l-4 border-[var(--scale-gold)] px-4 py-3 text-sm">
                  Linked to your existing registration ID: <span className="font-mono text-xs">{regId}</span>
                </div>
              )}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <F label="Student name" req><Input value={form.name} onChange={set("name")} required data-testid="schol-name" /></F>
                <F label="Email" req><Input type="email" value={form.email} onChange={set("email")} required data-testid="schol-email" /></F>
                <F label="School" req><Input value={form.school} onChange={set("school")} required data-testid="schol-school" /></F>
                <F label="Grade" req><Input value={form.grade} onChange={set("grade")} required data-testid="schol-grade" /></F>
                <F label="Phone" req><Input value={form.phone} onChange={set("phone")} required data-testid="schol-phone" /></F>
                <F label="Parent name" req><Input value={form.parent_name} onChange={set("parent_name")} required data-testid="schol-parent-name" /></F>
                <F label="Parent email" req full><Input type="email" value={form.parent_email} onChange={set("parent_email")} required data-testid="schol-parent-email" /></F>
              </div>
              <F label="Proof of financial situation (describe briefly OR paste link to document)" req>
                <Textarea rows={4} value={form.financial_proof} onChange={set("financial_proof")} required data-testid="schol-proof"
                  placeholder="e.g. Family income, dependents, or a public link (Google Drive) to supporting documents." />
              </F>
              <F label="Upload a supporting document (optional — PDF / JPG / PNG, max 10 MB)">
                {proofFile ? (
                  <div className="flex items-center justify-between bg-[var(--scale-cream)] border border-[var(--scale-gold)]/60 px-3 py-2" data-testid="proof-file-attached">
                    <div className="flex items-center gap-2 text-sm">
                      <FileCheck2 size={16} className="text-[var(--scale-crimson)]" />
                      <span className="font-medium">{proofFile.original_filename}</span>
                      <span className="text-xs text-black/50">({Math.round(proofFile.size / 1024)} KB)</span>
                    </div>
                    <button type="button" onClick={clearFile} className="text-black/50 hover:text-[var(--scale-crimson)]" data-testid="proof-file-clear">
                      <X size={14} />
                    </button>
                  </div>
                ) : (
                  <div>
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".pdf,.jpg,.jpeg,.png,.webp,application/pdf,image/jpeg,image/png,image/webp"
                      onChange={onPickFile}
                      className="hidden"
                      data-testid="proof-file-input"
                    />
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      disabled={uploading}
                      className="btn-outline-dark text-sm w-full justify-center"
                      data-testid="proof-file-pick"
                    >
                      {uploading ? <><Loader2 size={14} className="animate-spin" /> Uploading…</> : <><Upload size={14} /> Choose file</>}
                    </button>
                    <p className="text-xs text-black/50 mt-1">Review team only — files are stored securely and visible only to SCALE admins.</p>
                  </div>
                )}
              </F>
              <F label="Why do you want to participate in this event?" req>
                <Textarea rows={4} value={form.why_participate} onChange={set("why_participate")} required data-testid="schol-why" />
              </F>
              <button disabled={busy} className="btn-crimson justify-center mt-2" data-testid="schol-submit">
                {busy ? "Submitting..." : "Submit Scholarship Application"}
              </button>
              <p className="text-xs text-black/50">All applications are confidential. We will not share your details with anyone outside the SCALE review committee.</p>
            </form>
          )}
        </div>
      </section>
    </div>
  );
}

function F({ label, children, req, full }) {
  return (
    <div className={full ? "md:col-span-2" : ""}>
      <Label className="text-xs uppercase tracking-wider font-semibold text-black/70">
        {label} {req && <span className="text-[var(--scale-crimson)]">*</span>}
      </Label>
      <div className="mt-1.5">{children}</div>
    </div>
  );
}
