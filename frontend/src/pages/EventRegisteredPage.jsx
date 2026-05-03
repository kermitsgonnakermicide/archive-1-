import React, { useEffect, useState, useCallback, useMemo } from "react";
import { useParams, useNavigate, useSearchParams, Link } from "react-router-dom";
import { eventMaterialsApi, eventSubmissionsApi, registrationsApi } from "../lib/api";
import { toast } from "sonner";
import {
  Calendar, MapPin, Download, ExternalLink, Upload, FileText, Image as ImageIcon,
  Video, Music, File as FileIcon, Trash2, CheckCircle2, Loader2, ArrowLeft,
} from "lucide-react";

function iconFor(content_type = "", filename = "") {
  const c = content_type.toLowerCase();
  const ext = (filename.split(".").pop() || "").toLowerCase();
  if (c.startsWith("image/") || ["png", "jpg", "jpeg", "webp", "gif"].includes(ext)) return ImageIcon;
  if (c.startsWith("video/") || ["mp4", "mov", "avi", "webm"].includes(ext)) return Video;
  if (c.startsWith("audio/") || ["mp3", "wav", "m4a"].includes(ext)) return Music;
  if (ext === "pdf" || c.includes("pdf")) return FileText;
  if (["doc", "docx", "txt", "md", "rtf"].includes(ext)) return FileText;
  return FileIcon;
}

function formatSize(bytes = 0) {
  if (!bytes) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function EventRegisteredPage() {
  const { id: eventId } = useParams();
  const [params] = useSearchParams();
  const regId = params.get("reg");
  const navigate = useNavigate();

  const [stage, setStage] = useState("loading"); // loading | unpaid | notfound | ready
  const [materials, setMaterials] = useState(null);
  const [reg, setReg] = useState(null);
  const [mySubmission, setMySubmission] = useState(null);

  const load = useCallback(async () => {
    if (!regId) {
      // No reg_id → send to event page so they can register.
      navigate(`/events/${eventId}`, { replace: true });
      return;
    }
    try {
      const r = await registrationsApi.get(regId);
      setReg(r);
      if (r.event_id && r.event_id !== eventId) {
        // Mismatched event id — redirect to the correct one.
        navigate(`/events/${r.event_id}/registered?reg=${regId}`, { replace: true });
        return;
      }
    } catch {
      setStage("notfound");
      return;
    }
    try {
      const m = await eventMaterialsApi.get(eventId, regId);
      setMaterials(m);
      try {
        const sub = await eventSubmissionsApi.mine(eventId, regId);
        setMySubmission(sub && sub.exists === false ? null : sub);
      } catch { /* ignore — no prior submission */ }
      setStage("ready");
    } catch (err) {
      const code = err?.response?.status;
      if (code === 402) setStage("unpaid");
      else if (code === 404) setStage("notfound");
      else { toast.error("Failed to load event materials"); setStage("notfound"); }
    }
  }, [eventId, regId, navigate]);

  useEffect(() => { load(); }, [load]);

  if (stage === "loading") {
    return <div className="min-h-screen flex items-center justify-center pt-20"><Loader2 className="animate-spin text-[var(--scale-crimson)]" /></div>;
  }

  if (stage === "notfound") {
    return (
      <div className="min-h-screen flex items-center justify-center pt-20 px-6" data-testid="registered-notfound">
        <div className="bg-white border border-black/10 p-10 max-w-md w-full text-center">
          <h1 className="font-serif font-black text-2xl mb-3">Registration not found</h1>
          <p className="text-sm text-black/60 mb-5">We couldn't find a registration that matches this link. Please check the email confirmation, or register below.</p>
          <Link to={`/events/${eventId}`} className="btn-crimson justify-center w-full">Go to event page</Link>
        </div>
      </div>
    );
  }

  if (stage === "unpaid") {
    return (
      <div className="min-h-screen flex items-center justify-center pt-20 px-6" data-testid="registered-unpaid">
        <div className="bg-white border border-black/10 p-10 max-w-md w-full text-center">
          <div className="text-[10px] tracking-[0.28em] uppercase font-bold text-[var(--scale-crimson)] mb-2">Access Gated</div>
          <h1 className="font-serif font-black text-2xl mb-3">Complete your payment to access event materials</h1>
          <p className="text-sm text-black/70 mb-5">{reg?.event_title || "This event"} materials, briefings, and the submission portal unlock the moment your payment is confirmed.</p>
          <Link to={`/payment/${regId}`} className="btn-crimson justify-center w-full mb-2" data-testid="registered-complete-payment-btn">
            Complete Payment (₹{Math.round(reg?.amount_inr || 500)})
          </Link>
          <Link to={`/events/${eventId}/scholarship?reg=${regId}`} className="btn-outline-dark justify-center w-full text-sm">
            Apply for Scholarship Instead
          </Link>
        </div>
      </div>
    );
  }

  return <ReadyView eventId={eventId} regId={regId} materials={materials} reg={reg} mySubmission={mySubmission} onSubmissionUpdate={setMySubmission} />;
}

function ReadyView({ eventId, regId, materials, reg, mySubmission, onSubmissionUpdate }) {
  return (
    <div className="min-h-screen bg-[var(--scale-offwhite)] pt-20 md:pt-24 pb-16" data-testid="registered-page">
      <div className="max-container max-w-5xl">
        <Link to={`/events/${eventId}`} className="inline-flex items-center gap-1 text-xs text-black/60 hover:text-[var(--scale-crimson)] mb-4">
          <ArrowLeft size={14} /> Event page
        </Link>

        <div className="dark-red-section text-white p-6 md:p-10 mb-6">
          <div className="text-[10px] tracking-[0.28em] uppercase font-bold text-[var(--scale-goldlight)] mb-2">
            You're In · Registered participant
          </div>
          <h1 className="font-serif font-black text-3xl md:text-5xl leading-[1.05]">{materials.event_title}</h1>
          <div className="flex flex-wrap gap-x-6 gap-y-2 mt-5 text-sm text-white/85">
            {materials.event_date && <span className="inline-flex items-center gap-1.5"><Calendar size={14} /> {materials.event_date}</span>}
            {materials.event_location && <span className="inline-flex items-center gap-1.5"><MapPin size={14} /> {materials.event_location}</span>}
          </div>
        </div>

        {/* Notes */}
        {materials.notes && (
          <section className="bg-white border-l-4 border-[var(--scale-gold)] p-6 mb-6" data-testid="registered-notes">
            <div className="eyebrow text-[var(--scale-crimson)] mb-2">Briefing</div>
            <div className="text-base text-black/85 leading-relaxed whitespace-pre-line">{materials.notes}</div>
          </section>
        )}

        {/* Event description fallback */}
        {!materials.notes && materials.event_description && (
          <section className="bg-white p-6 mb-6">
            <div className="eyebrow mb-2">About this event</div>
            <p className="text-sm text-black/75 whitespace-pre-line">{materials.event_description}</p>
          </section>
        )}

        {/* Documents */}
        {(materials.documents || []).length > 0 && (
          <section className="bg-white p-6 md:p-8 mb-6" data-testid="registered-documents">
            <h2 className="font-serif font-bold text-xl mb-4">Documents</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {materials.documents.map((d, i) => {
                const Icon = iconFor(d.content_type, d.filename);
                const href = eventMaterialsApi.downloadUrl(eventId, d.file_id, regId);
                return (
                  <a key={d.id || d.file_id || `doc-${i}`} href={href} target="_blank" rel="noreferrer"
                     className="flex items-start gap-3 p-4 border border-black/10 hover:border-[var(--scale-crimson)] transition-colors group"
                     data-testid={`registered-doc-${d.file_id}`}>
                    <Icon className="text-[var(--scale-crimson)] mt-0.5 shrink-0" size={22} />
                    <div className="min-w-0 flex-1">
                      <div className="font-semibold text-sm truncate">{d.label || d.filename}</div>
                      <div className="text-xs text-black/50 truncate">{d.filename}{d.size ? ` · ${formatSize(d.size)}` : ""}</div>
                    </div>
                    <Download size={16} className="text-black/40 group-hover:text-[var(--scale-crimson)]" />
                  </a>
                );
              })}
            </div>
          </section>
        )}

        {/* Links */}
        {(materials.links || []).length > 0 && (
          <section className="bg-white p-6 md:p-8 mb-6" data-testid="registered-links">
            <h2 className="font-serif font-bold text-xl mb-4">Useful links</h2>
            <div className="space-y-2">
              {materials.links.map((l, i) => (
                <a key={l.id || `link-${i}`} href={l.url} target="_blank" rel="noreferrer"
                   className="flex items-center gap-3 p-3 border border-black/10 hover:border-[var(--scale-crimson)] hover:bg-[var(--scale-cream)] transition-colors"
                   data-testid={`registered-link-${l.id}`}>
                  <ExternalLink className="text-[var(--scale-crimson)] shrink-0" size={16} />
                  <span className="font-semibold text-sm flex-1 min-w-0 truncate">{l.label}</span>
                  <span className="text-xs text-black/50 truncate max-w-[40%]">{l.url}</span>
                </a>
              ))}
            </div>
          </section>
        )}

        {/* Submission form */}
        <SubmissionForm
          eventId={eventId}
          regId={regId}
          existing={mySubmission}
          onSaved={onSubmissionUpdate}
        />
      </div>
    </div>
  );
}

function SubmissionForm({ eventId, regId, existing, onSaved }) {
  const [text, setText] = useState(existing?.text_response || "");
  const [files, setFiles] = useState(existing?.files || []);
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [justSaved, setJustSaved] = useState(false);

  const editing = useMemo(() => !!existing, [existing]);

  useEffect(() => {
    setText(existing?.text_response || "");
    setFiles(existing?.files || []);
  }, [existing]);

  const pickFiles = async (e) => {
    const list = Array.from(e.target.files || []);
    if (!list.length) return;
    e.target.value = "";  // allow same file re-pick
    setUploading(true);
    try {
      for (const f of list) {
        try {
          const res = await eventSubmissionsApi.upload(eventId, regId, f);
          setFiles((prev) => [...prev, res]);
        } catch (err) {
          toast.error(err?.response?.data?.detail || `Upload failed: ${f.name}`);
        }
      }
    } finally { setUploading(false); }
  };

  const removeFile = (file_id) => setFiles((prev) => prev.filter((f) => f.file_id !== file_id));

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const res = await eventSubmissionsApi.submit(eventId, {
        registration_id: regId,
        text_response: text,
        files,
      });
      const fresh = await eventSubmissionsApi.mine(eventId, regId);
      onSaved(fresh);
      setJustSaved(true);
      setTimeout(() => setJustSaved(false), 3500);
      toast.success(res.action === "updated" ? "Submission updated" : "Submission received");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed to submit");
    } finally { setBusy(false); }
  };

  return (
    <section className="bg-white p-6 md:p-8" data-testid="submission-form">
      <div className="flex items-center justify-between gap-3 mb-4 flex-wrap">
        <div>
          <h2 className="font-serif font-bold text-xl">{editing ? "Your submission" : "Submit your entry"}</h2>
          {editing && (
            <p className="text-xs text-black/55 mt-1">
              Last {existing.created_at === existing.updated_at ? "submitted" : "updated"} {new Date(existing.updated_at).toLocaleString()}. You can update any time before the event.
            </p>
          )}
        </div>
        {justSaved && <span className="inline-flex items-center gap-1 text-xs font-semibold text-[var(--scale-crimson)]"><CheckCircle2 size={14} /> Saved</span>}
      </div>

      <form onSubmit={submit} className="space-y-4">
        <div>
          <label className="text-xs uppercase tracking-wider font-semibold text-black/70">Written response</label>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={6}
            placeholder="Share your answer, essay, analysis, or notes for this event…"
            className="mt-1.5 w-full border border-black/15 p-3 text-sm focus:border-[var(--scale-crimson)] outline-none"
            data-testid="submission-text"
          />
        </div>

        <div>
          <label className="text-xs uppercase tracking-wider font-semibold text-black/70 block mb-1.5">
            Attachments ({files.length})
          </label>
          {files.length > 0 && (
            <div className="space-y-1.5 mb-2">
              {files.map((f) => {
                const Icon = iconFor(f.content_type, f.filename);
                return (
                  <div key={f.file_id} className="flex items-center gap-2 border border-black/10 p-2 text-sm" data-testid={`submission-file-${f.file_id}`}>
                    <Icon size={16} className="text-black/60" />
                    <span className="flex-1 min-w-0 truncate">{f.filename}</span>
                    <span className="text-xs text-black/40">{formatSize(f.size)}</span>
                    <button type="button" onClick={() => removeFile(f.file_id)} className="text-black/40 hover:text-[var(--scale-crimson)]" aria-label="Remove">
                      <Trash2 size={14} />
                    </button>
                  </div>
                );
              })}
            </div>
          )}
          <label className="btn-outline-dark text-xs cursor-pointer inline-flex" data-testid="submission-attach-btn">
            <Upload size={14} /> {uploading ? "Uploading…" : "Attach files"}
            <input type="file" multiple className="hidden" onChange={pickFiles} accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.txt,.md,.csv,.zip,.jpg,.jpeg,.png,.webp,.gif,.mp4,.mp3,.wav,.m4a" />
          </label>
          <p className="text-[11px] text-black/45 mt-1">PDF, DOC, PPT, XLS, images, audio, video. Max 25 MB per file.</p>
        </div>

        <div className="flex items-center gap-3 pt-2 border-t border-black/10">
          <button type="submit" disabled={busy} className="btn-crimson text-sm" data-testid="submission-submit-btn">
            {busy ? <><Loader2 className="animate-spin" size={14} /> Saving…</> : editing ? "Update submission" : "Submit"}
          </button>
          <span className="text-xs text-black/55">You can update your submission any time before the event.</span>
        </div>
      </form>
    </section>
  );
}
