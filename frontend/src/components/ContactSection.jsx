import React, { useState } from "react";
import { useApp } from "../context/AppContext";
import { toast } from "sonner";
import { formsApi } from "../lib/api";
import Editable from "./Editable";
import { Input } from "./ui/input";
import { Textarea } from "./ui/textarea";
import { Label } from "./ui/label";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "./ui/select";
import { Mail, Instagram, Linkedin } from "lucide-react";

export default function ContactSection() {
  const { content } = useApp();
  const [form, setForm] = useState({ name: "", school: "", subject: "General Inquiry", message: "", email: "" });
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await formsApi.contact(form);
      toast.success("Message sent. We'll respond soon.");
      setForm({ name: "", school: "", subject: "General Inquiry", message: "", email: "" });
    } catch { toast.error("Message failed to send."); }
    finally { setBusy(false); }
  };

  return (
    <section id="contact" className="dark-red-section py-16 md:py-24" data-testid="contact-section">
      <div className="max-container grid grid-cols-1 lg:grid-cols-12 gap-10">
        <div className="lg:col-span-5 text-white reveal">
          <Editable as="div" field="contact_eyebrow" value={content?.contact_eyebrow} className="eyebrow-gold block" />
          <Editable
            as="h2"
            field="contact_headline"
            value={content?.contact_headline}
            multiline
            className="font-serif font-black text-3xl md:text-5xl leading-[1.1] mb-6 block"
          />
          <div className="space-y-4 text-white/85">
            <a href={`mailto:${content?.contact_email}`} className="flex items-center gap-3 hover:text-[var(--scale-goldlight)] transition" data-testid="contact-email-link">
              <Mail size={18} className="text-[var(--scale-goldlight)]" />
              <Editable field="contact_email" value={content?.contact_email} />
            </a>
            <a href={`https://instagram.com/${(content?.contact_instagram || "").replace("@", "")}`} target="_blank" rel="noreferrer" className="flex items-center gap-3 hover:text-[var(--scale-goldlight)] transition">
              <Instagram size={18} className="text-[var(--scale-goldlight)]" />
              <Editable field="contact_instagram" value={content?.contact_instagram} />
            </a>
            <a href="https://linkedin.com" target="_blank" rel="noreferrer" className="flex items-center gap-3 hover:text-[var(--scale-goldlight)] transition">
              <Linkedin size={18} className="text-[var(--scale-goldlight)]" />
              <Editable field="contact_linkedin" value={content?.contact_linkedin} />
            </a>
          </div>
        </div>

        <div className="lg:col-span-7 reveal">
          <form onSubmit={submit} className="bg-white text-black p-6 md:p-8 grid gap-4" data-testid="contact-form">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Field label="Name" req><Input value={form.name} onChange={set("name")} required data-testid="contact-name" /></Field>
              <Field label="School / Organisation"><Input value={form.school} onChange={set("school")} data-testid="contact-school" /></Field>
            </div>
            <Field label="Subject" req>
              <Select value={form.subject} onValueChange={(v) => setForm((f) => ({ ...f, subject: v }))}>
                <SelectTrigger data-testid="contact-subject"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="General Inquiry">General Inquiry</SelectItem>
                  <SelectItem value="Speaking Opportunity">Speaking Opportunity</SelectItem>
                  <SelectItem value="Partnership">Partnership</SelectItem>
                  <SelectItem value="Other">Other</SelectItem>
                </SelectContent>
              </Select>
            </Field>
            <Field label="Message" req><Textarea rows={5} value={form.message} onChange={set("message")} required data-testid="contact-message" /></Field>
            <Field label="Contact Email" req><Input type="email" value={form.email} onChange={set("email")} required data-testid="contact-email" /></Field>
            <button disabled={busy} className="btn-crimson justify-center mt-2" data-testid="contact-submit">
              {busy ? "Sending..." : "Send Message"}
            </button>
          </form>
        </div>
      </div>
    </section>
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
