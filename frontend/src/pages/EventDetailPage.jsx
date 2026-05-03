import React, { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { eventsApi, registrationsApi } from "../lib/api";
import { useApp } from "../context/AppContext";
import { toast } from "sonner";
import Editable from "../components/Editable";
import { Input } from "../components/ui/input";
import { Textarea } from "../components/ui/textarea";
import { Label } from "../components/ui/label";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "../components/ui/select";
import { ArrowLeft, Calendar, MapPin, IndianRupee, Plus, Trash2, Users, User, Upload } from "lucide-react";
import { uploadsApi } from "../lib/api";

const emptyIndividual = {
  name: "", school: "", grade: "", email: "", phone: "",
  parent_name: "", parent_phone: "", parent_email: "",
};
const emptyMember = { name: "", school: "", grade: "", email: "", phone: "", extras: {} };

export default function EventDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { editing, refreshEvents, content } = useApp();
  const [event, setEvent] = useState(null);

  const [individual, setIndividual] = useState(emptyIndividual);
  const [teamName, setTeamName] = useState("");
  const [members, setMembers] = useState([{ ...emptyMember }, { ...emptyMember }, { ...emptyMember }]);
  const [teamParent, setTeamParent] = useState({ parent_name: "", parent_phone: "", parent_email: "" });
  const [extras, setExtras] = useState({});

  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(null);

  const load = async () => {
    try {
      const e = await eventsApi.get(id);
      setEvent(e);
      // Ensure members array length matches min team size
      const tmin = Math.max(2, e.team_size_min || 2);
      setMembers((curr) => (curr.length < tmin ? [...curr, ...Array(tmin - curr.length).fill().map(() => ({ ...emptyMember }))] : curr));
    } catch { toast.error("Event not found."); navigate("/"); }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [id]);

  const mode = event?.registration_mode || "individual";
  const tmin = event?.team_size_min || 2;
  const tmax = event?.team_size_max || 5;
  const extraFields = event?.extra_fields || [];

  const saveField = async (field, value) => {
    await eventsApi.update(id, { [field]: value });
    setEvent((e) => ({ ...e, [field]: value }));
    refreshEvents();
  };

  const addMember = () => {
    if (members.length >= tmax) return;
    setMembers([...members, { ...emptyMember }]);
  };
  const removeMember = (i) => {
    if (members.length <= tmin) return;
    setMembers(members.filter((_, idx) => idx !== i));
  };
  const setMember = (i, k) => (e) => {
    const next = members.map((m, idx) => (idx === i ? { ...m, [k]: e.target.value } : m));
    setMembers(next);
  };
  const setMemberExtra = (i, key) => (v) => {
    const next = members.map((m, idx) => (idx === i ? { ...m, extras: { ...(m.extras || {}), [key]: v } } : m));
    setMembers(next);
  };
  const setInd = (k) => (e) => setIndividual((f) => ({ ...f, [k]: e.target.value }));
  const setPar = (k) => (e) => setTeamParent((f) => ({ ...f, [k]: e.target.value }));
  const setExtra = (k) => (v) => setExtras((x) => ({ ...x, [k]: v }));

  const eligibilityText = useMemo(() => {
    return event?.eligibility || content?.event_detail_eligibility_body || "Open to students in grades 9-12.";
  }, [event, content]);

  // Split extras by scope. In individual mode, all extras are team-scope (single answer).
  const teamExtras = useMemo(
    () => (extraFields || []).filter((ef) => mode !== "team" || (ef.scope || "team") !== "member"),
    [extraFields, mode]
  );
  const memberExtras = useMemo(
    () => (mode === "team" ? (extraFields || []).filter((ef) => ef.scope === "member") : []),
    [extraFields, mode]
  );

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const payload = { event_id: id, extras };
      if (mode === "team") {
        payload.team_name = teamName;
        payload.members = members;
        Object.assign(payload, teamParent);
      } else {
        Object.assign(payload, individual);
      }
      const res = await registrationsApi.create(payload);
      setDone(res);
      toast.success("Registered! Check your inbox.");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Registration failed.");
    } finally { setBusy(false); }
  };

  if (!event) return <div className="min-h-screen flex items-center justify-center">Loading…</div>;

  return (
    <div className="min-h-screen bg-[var(--scale-offwhite)] pt-20" data-testid="event-detail-page">
      <section className="dark-red-section py-12 md:py-20">
        <div className="max-container">
          <Link to="/#events" className="text-white/70 hover:text-white text-xs uppercase tracking-[0.28em] flex items-center gap-2 mb-6">
            <ArrowLeft size={14} /> Back to Events
          </Link>
          <div className={`inline-block text-[10px] tracking-[0.28em] uppercase font-bold mb-3 ${
            event.registration_open === false
              ? "text-white/70"
              : event.status === "live" ? "text-[var(--scale-goldlight)]" : "text-white/70"
          }`}>
            {event.registration_open === false
              ? "○ Registration Closed"
              : event.status === "live" ? "● Live · Registration Open" : "Coming Soon"}
            <span className="ml-3 inline-flex items-center gap-1">
              {mode === "team" ? <><Users size={12} /> Team · {tmin}-{tmax}</> : <><User size={12} /> Individual</>}
            </span>
          </div>
          <Editable
            as="h1"
            value={event.title}
            className="font-serif font-black text-4xl md:text-6xl text-white leading-[1.05] block"
            onSave={(v) => saveField("title", v)}
            testId="event-detail-title"
          />
          <div className="mt-6 flex flex-wrap gap-x-8 gap-y-3 text-white/85 text-sm">
            <span className="flex items-center gap-2"><Calendar size={14} className="text-[var(--scale-goldlight)]" />
              <Editable value={event.date} onSave={(v) => saveField("date", v)} placeholder="Date TBA" />
            </span>
            <span className="flex items-center gap-2"><MapPin size={14} className="text-[var(--scale-goldlight)]" />
              <Editable value={event.location || "TBA"} onSave={(v) => saveField("location", v)} placeholder="Location" />
            </span>
            <span className="flex items-center gap-2"><IndianRupee size={14} className="text-[var(--scale-goldlight)]" />
              {editing ? (
                <input
                  type="number"
                  defaultValue={event.price_inr || 500}
                  onBlur={(e) => saveField("price_inr", parseFloat(e.target.value || "0"))}
                  className="bg-transparent border-b border-white/40 text-white w-24"
                />
              ) : (
                <span>{event.price_inr || 500} registration fee</span>
              )}
            </span>
          </div>
        </div>
      </section>

      <section className="py-12 md:py-20">
        <div className="max-container grid grid-cols-1 lg:grid-cols-12 gap-10">
          <div className="lg:col-span-7">
            <Editable as="div" field="event_detail_about_label" value={content?.event_detail_about_label || "About this event"} className="eyebrow block" />
            <Editable
              as="div"
              value={event.about}
              multiline
              className="text-base md:text-lg leading-relaxed text-black/80 whitespace-pre-line block"
              onSave={(v) => saveField("about", v)}
              testId="event-detail-about"
              placeholder="Add long-form description here."
            />

            <div className="gold-left mt-10">
              <Editable as="div" field="event_detail_eligibility_label" value={content?.event_detail_eligibility_label || "Eligibility"} className="eyebrow-gold block" />
              <Editable
                as="p"
                value={eligibilityText}
                multiline
                className="font-serif italic text-lg text-black/80 block"
                onSave={(v) => saveField("eligibility", v)}
                placeholder="Set per-event eligibility (overrides global)."
              />
            </div>

            <div className="mt-10 bg-[var(--scale-cream)] border-l-4 border-[var(--scale-gold)] p-5">
              <Editable as="div" field="event_detail_scholarship_label" value={content?.event_detail_scholarship_label || "Need financial support?"} className="font-serif font-bold mb-1 block" />
              <Editable
                as="p"
                field="event_detail_scholarship_body"
                value={content?.event_detail_scholarship_body}
                multiline
                className="text-sm text-black/75 mb-3 block"
              />
              <Link to={`/events/${event.id}/scholarship`} className="btn-outline-dark text-sm" data-testid="event-scholarship-link">
                Apply for Scholarship
              </Link>
            </div>
          </div>

          {/* Registration form — dynamic per mode */}
          <div className="lg:col-span-5">
            <div className="bg-white border border-black/10 p-6 md:p-8 sticky top-28" data-testid="event-registration-form">
              {event.registration_open === false ? (
                <div className="text-center py-6" data-testid="registration-closed">
                  <div className="text-[10px] tracking-[0.28em] uppercase font-bold text-[var(--scale-crimson)] mb-3">Registration closed</div>
                  <h3 className="font-serif font-black text-2xl mb-3">Not accepting entries right now</h3>
                  <p className="text-sm text-black/70 mb-5">
                    {event.registration_closed_message || "Registration is currently closed for this event. Check back soon."}
                  </p>
                  <Link to={`/events/${event.id}/scholarship`} className="btn-outline-dark w-full justify-center text-sm">
                    Apply for Scholarship
                  </Link>
                  <Link to="/#contact" className="block text-xs uppercase tracking-[0.28em] text-black/50 hover:text-black mt-4">
                    Contact us for questions →
                  </Link>
                </div>
              ) : done ? (
                <div className="text-center" data-testid="registration-success">
                  <div className="text-4xl mb-3">✓</div>
                  <h3 className="font-serif font-black text-2xl mb-2">Registration received</h3>
                  <p className="text-sm text-black/70 mb-4">
                    Confirmation emails sent. Complete payment now to secure {mode === "team" ? "your team's" : "your"} spot.
                  </p>
                  <div className="bg-[var(--scale-cream)] border-l-4 border-[var(--scale-gold)] p-3 mb-5 text-left" data-testid="spam-folder-hint">
                    <div className="text-[10px] tracking-[0.28em] uppercase font-bold text-[var(--scale-crimson)] mb-1">
                      One quick thing
                    </div>
                    <p className="text-xs text-black/75 leading-relaxed">
                      Watch your <strong>inbox &amp; spam folder</strong> for an email from <strong>SCALE India</strong>. Some providers (Gmail Promotions, Outlook Junk) may filter the first message — mark it "Not spam" so future updates land cleanly.
                    </p>
                  </div>
                  <Link to={`/payment/${done.registration_id}`} className="btn-crimson w-full justify-center mb-2" data-testid="goto-payment-btn">
                    Complete Payment (₹{Math.round(event.price_inr || 500)})
                  </Link>
                  <Link to={`/events/${event.id}/scholarship?reg=${done.registration_id}`} className="btn-outline-dark w-full justify-center text-sm">
                    Apply for Scholarship Instead
                  </Link>
                </div>
              ) : (
                <>
                  <div className="eyebrow">Register Now</div>
                  <h3 className="font-serif font-black text-2xl mb-1">
                    {mode === "team" ? "Reserve your team" : "Reserve your spot"}
                  </h3>
                  <p className="text-sm text-black/60 mb-5">
                    {mode === "team" ? `Team of ${tmin}-${tmax}. ` : ""}Pay ₹{Math.round(event.price_inr || 500)} after registration via UPI or card.
                  </p>
                  <form onSubmit={submit} className="grid gap-3">
                    {mode === "team" ? (
                      <>
                        <Field label="Team name" req>
                          <Input value={teamName} onChange={(e) => setTeamName(e.target.value)} required data-testid="reg-team-name" />
                        </Field>

                        {members.map((m, i) => (
                          <div key={i} className="border border-black/10 p-3" data-testid={`reg-member-${i}`}>
                            <div className="flex items-center justify-between mb-2">
                              <div className="text-[10px] tracking-[0.28em] uppercase font-bold text-[var(--scale-crimson)]">
                                Member {i + 1}{i === 0 ? " · Captain" : ""}
                              </div>
                              {members.length > tmin && (
                                <button type="button" onClick={() => removeMember(i)} className="text-black/40 hover:text-[var(--scale-crimson)]" data-testid={`reg-member-remove-${i}`}>
                                  <Trash2 size={12} />
                                </button>
                              )}
                            </div>
                            <div className="grid grid-cols-1 gap-2">
                              <Input placeholder="Full name" value={m.name} onChange={setMember(i, "name")} required data-testid={`reg-member-name-${i}`} />
                              <Input placeholder="School" value={m.school} onChange={setMember(i, "school")} required data-testid={`reg-member-school-${i}`} />
                              <div className="grid grid-cols-2 gap-2">
                                <Input placeholder="Grade" value={m.grade} onChange={setMember(i, "grade")} required data-testid={`reg-member-grade-${i}`} />
                                <Input placeholder="Phone" value={m.phone} onChange={setMember(i, "phone")} required data-testid={`reg-member-phone-${i}`} />
                              </div>
                              <Input type="email" placeholder="Email" value={m.email} onChange={setMember(i, "email")} required data-testid={`reg-member-email-${i}`} />
                              {memberExtras.map((ef) => (
                                <ExtraFieldInput
                                  key={ef.key}
                                  field={ef}
                                  value={(m.extras || {})[ef.key]}
                                  onChange={setMemberExtra(i, ef.key)}
                                  testIdPrefix={`reg-member-${i}-extra-${ef.key}`}
                                />
                              ))}
                            </div>
                          </div>
                        ))}

                        {members.length < tmax && (
                          <button type="button" onClick={addMember} className="btn-outline-dark text-sm justify-center" data-testid="reg-add-member">
                            <Plus size={14} /> Add team member ({members.length}/{tmax})
                          </button>
                        )}

                        <div className="mt-2 pt-3 border-t border-black/10">
                          <div className="eyebrow text-[var(--scale-crimson)]">Captain's Parent / Guardian</div>
                        </div>
                        <Field label="Parent name" req><Input value={teamParent.parent_name} onChange={setPar("parent_name")} required data-testid="reg-parent-name" /></Field>
                        <Field label="Parent phone" req><Input value={teamParent.parent_phone} onChange={setPar("parent_phone")} required data-testid="reg-parent-phone" /></Field>
                        <Field label="Parent email" req><Input type="email" value={teamParent.parent_email} onChange={setPar("parent_email")} required data-testid="reg-parent-email" /></Field>
                      </>
                    ) : (
                      <>
                        <Field label="Student name" req><Input value={individual.name} onChange={setInd("name")} required data-testid="reg-name" /></Field>
                        <Field label="School" req><Input value={individual.school} onChange={setInd("school")} required data-testid="reg-school" /></Field>
                        <div className="grid grid-cols-2 gap-3">
                          <Field label="Grade" req><Input value={individual.grade} onChange={setInd("grade")} required data-testid="reg-grade" /></Field>
                          <Field label="Phone" req><Input value={individual.phone} onChange={setInd("phone")} required data-testid="reg-phone" /></Field>
                        </div>
                        <Field label="Email" req><Input type="email" value={individual.email} onChange={setInd("email")} required data-testid="reg-email" /></Field>

                        <div className="mt-2 pt-3 border-t border-black/10">
                          <div className="eyebrow text-[var(--scale-crimson)]">Parent / Guardian</div>
                        </div>
                        <Field label="Parent name" req><Input value={individual.parent_name} onChange={setInd("parent_name")} required data-testid="reg-parent-name" /></Field>
                        <Field label="Parent phone" req><Input value={individual.parent_phone} onChange={setInd("parent_phone")} required data-testid="reg-parent-phone" /></Field>
                        <Field label="Parent email" req><Input type="email" value={individual.parent_email} onChange={setInd("parent_email")} required data-testid="reg-parent-email" /></Field>
                      </>
                    )}

                    {/* Extra custom fields — team-scoped (or all, if individual mode) */}
                    {teamExtras.length > 0 && (
                      <div className="mt-2 pt-3 border-t border-black/10">
                        <div className="eyebrow text-[var(--scale-crimson)]">A few more questions</div>
                      </div>
                    )}
                    {teamExtras.map((ef) => (
                      <ExtraFieldInput
                        key={ef.key}
                        field={ef}
                        value={extras[ef.key]}
                        onChange={setExtra(ef.key)}
                        testIdPrefix={`reg-extra-${ef.key}`}
                      />
                    ))}

                    <button disabled={busy} className="btn-crimson justify-center mt-2" data-testid="reg-submit">
                      {busy ? "Submitting..." : `Register & Continue to Payment`}
                    </button>
                    <p className="text-xs text-black/50 text-center">
                      {mode === "team" ? "All members and the captain's parent receive a confirmation email." : "Parent and student receive a confirmation email."}
                    </p>
                  </form>
                </>
              )}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

function Field({ label, children, req }) {
  return (
    <div>
      <Label className="text-xs uppercase tracking-wider font-semibold text-black/70">
        {label} {req && <span className="text-[var(--scale-crimson)]">*</span>}
      </Label>
      <div className="mt-1.5">{children}</div>
    </div>
  );
}

function ExtraFieldInput({ field, value, onChange, testIdPrefix }) {
  const [uploading, setUploading] = useState(false);
  const ef = field;
  const tid = testIdPrefix || `extra-${ef.key}`;
  const help = ef.help_text ? (
    <p className="text-[11px] text-black/50 mt-1">{ef.help_text}</p>
  ) : null;

  if (ef.type === "checkbox") {
    return (
      <div>
        <label className="flex items-start gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={value === true || value === "true"}
            onChange={(e) => onChange(e.target.checked)}
            data-testid={tid}
            className="mt-1"
          />
          <span className="text-sm text-black/85">
            {ef.label || ef.key} {ef.required && <span className="text-[var(--scale-crimson)]">*</span>}
          </span>
        </label>
        {help}
      </div>
    );
  }

  return (
    <Field label={ef.label || ef.key} req={ef.required}>
      {ef.type === "textarea" ? (
        <Textarea rows={3} value={value || ""} onChange={(e) => onChange(e.target.value)} required={ef.required} data-testid={tid} />
      ) : ef.type === "email" ? (
        <Input type="email" value={value || ""} onChange={(e) => onChange(e.target.value)} required={ef.required} data-testid={tid} />
      ) : ef.type === "number" ? (
        <Input type="number" value={value ?? ""} onChange={(e) => onChange(e.target.value)} required={ef.required} data-testid={tid} />
      ) : ef.type === "yesno" ? (
        <Select value={value || ""} onValueChange={onChange}>
          <SelectTrigger data-testid={tid}><SelectValue placeholder="Choose…" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="yes">Yes</SelectItem>
            <SelectItem value="no">No</SelectItem>
          </SelectContent>
        </Select>
      ) : ef.type === "select" ? (
        <Select value={value || ""} onValueChange={onChange}>
          <SelectTrigger data-testid={tid}><SelectValue placeholder="Choose…" /></SelectTrigger>
          <SelectContent>
            {(ef.options || []).map((o) => <SelectItem key={o} value={o}>{o}</SelectItem>)}
          </SelectContent>
        </Select>
      ) : ef.type === "radio" ? (
        <div className="space-y-1.5">
          {(ef.options || []).map((o) => (
            <label key={o} className="flex items-center gap-2 cursor-pointer text-sm">
              <input
                type="radio"
                name={`radio-${ef.key}-${testIdPrefix}`}
                checked={value === o}
                onChange={() => onChange(o)}
                data-testid={`${tid}-${o.replace(/\s+/g, "-")}`}
              />
              {o}
            </label>
          ))}
        </div>
      ) : ef.type === "file" ? (
        <div>
          <label className="btn-outline-dark text-xs cursor-pointer w-full justify-center" data-testid={tid}>
            <Upload size={14} /> {uploading ? "Uploading…" : (value ? "Replace file" : "Choose file (PDF/JPG/PNG)")}
            <input
              type="file"
              accept=".pdf,.jpg,.jpeg,.png,.webp"
              className="hidden"
              onChange={async (e) => {
                const f = e.target.files?.[0];
                if (!f) return;
                setUploading(true);
                try {
                  const res = await uploadsApi.scholarshipProof(f);
                  onChange(res.id);
                } catch {
                  /* eslint-disable-next-line no-alert */
                  alert("Upload failed. Try a smaller file (≤10MB).");
                } finally { setUploading(false); }
              }}
            />
          </label>
          {value && <p className="text-[11px] text-black/50 mt-1">File uploaded ✓</p>}
        </div>
      ) : (
        <Input value={value || ""} onChange={(e) => onChange(e.target.value)} required={ef.required} data-testid={tid} />
      )}
      {help}
    </Field>
  );
}
