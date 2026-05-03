import React, { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { pagesApi } from "../lib/api";
import { useApp } from "../context/AppContext";
import { toast } from "sonner";

export default function CustomPage() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const { editing, isAdmin, refreshPages } = useApp();
  const [page, setPage] = useState(null);
  const [error, setError] = useState(null);

  const load = async () => {
    try {
      const p = await pagesApi.get(slug);
      setPage(p);
    } catch (e) {
      setError(e?.response?.status === 404 ? "Page not found" : "Failed to load page");
    }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [slug]);

  const updateBlock = async (blockId, props) => {
    if (!page) return;
    const blocks = page.blocks.map((b) => (b.id === blockId ? { ...b, props: { ...b.props, ...props } } : b));
    const next = { ...page, blocks };
    setPage(next);
    try { await pagesApi.update(page.id, { blocks }); } catch { /* will retry on next save */ }
  };

  const updateMeta = async (patch) => {
    if (!page) return;
    const next = { ...page, ...patch };
    setPage(next);
    try {
      await pagesApi.update(page.id, patch);
      await refreshPages();
      toast.success(patch.show_in_nav === false ? "Hidden from navbar" : patch.show_in_nav === true ? "Visible in navbar" : patch.published === false ? "Unpublished" : patch.published === true ? "Published" : "Saved");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Save failed");
      setPage(page); // revert
    }
  };

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center pt-20" data-testid="custom-page-error">
        <div className="text-center">
          <div className="font-serif text-3xl mb-2">{error}</div>
          <Link to="/" className="text-[var(--scale-crimson)] underline">Back to home</Link>
        </div>
      </div>
    );
  }
  if (!page) return <div className="min-h-screen flex items-center justify-center pt-20">Loading…</div>;

  return (
    <div className="min-h-screen bg-[var(--scale-offwhite)] pt-16 md:pt-20" data-testid={`custom-page-${page.slug}`}>
      {isAdmin && (
        <div className="bg-[var(--scale-cream)] border-b border-[var(--scale-gold)] py-2">
          <div className="max-container flex items-center justify-between text-sm flex-wrap gap-2">
            <span className="text-[10px] tracking-[0.28em] uppercase font-bold text-[var(--scale-crimson)]">
              Custom page · /{page.slug} {!page.published && "· Draft"}
            </span>
            <div className="flex items-center gap-4 flex-wrap">
              <label className="flex items-center gap-1.5 text-xs cursor-pointer" data-testid="inline-show-in-nav">
                <input
                  type="checkbox"
                  checked={page.show_in_nav !== false}
                  onChange={(e) => updateMeta({ show_in_nav: e.target.checked })}
                />
                Show in navbar
              </label>
              <label className="flex items-center gap-1.5 text-xs cursor-pointer" data-testid="inline-published">
                <input
                  type="checkbox"
                  checked={page.published !== false}
                  onChange={(e) => updateMeta({ published: e.target.checked })}
                />
                Published
              </label>
              <button onClick={() => navigate("/admin")} className="text-xs underline">Edit in Admin →</button>
            </div>
          </div>
        </div>
      )}
      {(page.blocks || []).map((b) => (
        <BlockRenderer key={b.id} block={b} editing={editing} onUpdate={(props) => updateBlock(b.id, props)} />
      ))}
      {(!page.blocks || page.blocks.length === 0) && (
        <div className="max-container py-24 text-center">
          <div className="text-[10px] tracking-[0.28em] uppercase font-bold text-[var(--scale-crimson)] mb-3">{page.title}</div>
          <h1 className="font-serif font-black text-4xl md:text-5xl mb-4">No content yet</h1>
          <p className="text-black/60 max-w-xl mx-auto">This page is empty. {isAdmin && <>Open the <Link to="/admin" className="underline">Admin → Pages</Link> tab to add blocks.</>}</p>
        </div>
      )}
    </div>
  );
}

function InlineText({ value, onSave, multiline, className, placeholder }) {
  // Lightweight inline editor — only when admin clicks. Otherwise renders text.
  const { editing } = useApp();
  const [draft, setDraft] = useState(value || "");
  useEffect(() => { setDraft(value || ""); }, [value]);
  if (!editing) {
    return <span className={className}>{value || placeholder || ""}</span>;
  }
  const Tag = multiline ? "textarea" : "input";
  return (
    <Tag
      value={draft}
      onChange={(e) => setDraft(e.target.value)}
      onBlur={() => { if (draft !== value) onSave(draft); }}
      placeholder={placeholder}
      rows={multiline ? 4 : undefined}
      className={`${className} bg-white/80 border border-dashed border-[var(--scale-gold)] px-2 py-1 outline-none focus:bg-white w-full`}
    />
  );
}

function BlockRenderer({ block, onUpdate }) {
  const p = block.props || {};
  switch (block.type) {
    case "hero":
      return (
        <section className="dark-red-section py-16 md:py-24" data-testid={`block-${block.id}`}>
          <div className="max-container">
            <div className="text-[10px] tracking-[0.28em] uppercase font-bold text-[var(--scale-goldlight)] mb-3">
              <InlineText value={p.eyebrow} onSave={(v) => onUpdate({ eyebrow: v })} placeholder="Eyebrow" />
            </div>
            <h1 className="font-serif font-black text-4xl md:text-6xl text-white leading-[1.05] block">
              <InlineText value={p.headline} onSave={(v) => onUpdate({ headline: v })} placeholder="Headline" />
            </h1>
            <p className="mt-5 text-white/80 max-w-2xl text-base md:text-lg">
              <InlineText value={p.subtext} multiline onSave={(v) => onUpdate({ subtext: v })} placeholder="Subtext" />
            </p>
            {(p.cta_label || p.cta_link) && (
              <a href={p.cta_link || "#"} className="btn-gold text-sm mt-8 inline-flex">
                {p.cta_label || "Learn more"}
              </a>
            )}
          </div>
        </section>
      );
    case "section":
      return (
        <section className="py-12 md:py-20" data-testid={`block-${block.id}`}>
          <div className="max-container">
            {p.eyebrow && <div className="eyebrow"><InlineText value={p.eyebrow} onSave={(v) => onUpdate({ eyebrow: v })} /></div>}
            <h2 className="font-serif font-black text-3xl md:text-5xl mt-2 max-w-3xl">
              <InlineText value={p.headline} onSave={(v) => onUpdate({ headline: v })} placeholder="Section headline" />
            </h2>
            <div className="mt-6 max-w-3xl text-base md:text-lg leading-relaxed text-black/80 whitespace-pre-line">
              <InlineText value={p.body} multiline onSave={(v) => onUpdate({ body: v })} placeholder="Section body" />
            </div>
          </div>
        </section>
      );
    case "cards": {
      const items = p.items || [];
      return (
        <section className="py-12 md:py-20 bg-white border-y border-black/10" data-testid={`block-${block.id}`}>
          <div className="max-container">
            {p.eyebrow && <div className="eyebrow"><InlineText value={p.eyebrow} onSave={(v) => onUpdate({ eyebrow: v })} /></div>}
            {p.headline && (
              <h2 className="font-serif font-black text-3xl md:text-5xl mt-2 max-w-3xl mb-10">
                <InlineText value={p.headline} onSave={(v) => onUpdate({ headline: v })} />
              </h2>
            )}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {items.map((it, i) => (
                <div key={i} className="border border-black/10 p-6 hover:border-[var(--scale-crimson)] transition-colors">
                  <div className="font-serif font-bold text-xl mb-2 text-[var(--scale-crimson)]">{it.title}</div>
                  <p className="text-sm text-black/75 leading-relaxed whitespace-pre-line">{it.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      );
    }
    case "cta":
      return (
        <section className="py-12 md:py-16 bg-[var(--scale-cream)]" data-testid={`block-${block.id}`}>
          <div className="max-container text-center">
            <h2 className="font-serif font-black text-3xl md:text-4xl mb-4 max-w-2xl mx-auto">
              <InlineText value={p.headline} onSave={(v) => onUpdate({ headline: v })} placeholder="CTA headline" />
            </h2>
            {p.subtext && <p className="text-black/70 max-w-xl mx-auto mb-6"><InlineText value={p.subtext} multiline onSave={(v) => onUpdate({ subtext: v })} /></p>}
            {(p.cta_label || p.cta_link) && (
              <a href={p.cta_link || "#"} className="btn-crimson inline-flex">{p.cta_label || "Get started"}</a>
            )}
          </div>
        </section>
      );
    case "image":
      return (
        <section className="py-8 md:py-12" data-testid={`block-${block.id}`}>
          <div className="max-container">
            {p.url ? (
              <figure>
                <img src={p.url} alt={p.alt || ""} className="w-full h-auto" />
                {p.caption && <figcaption className="text-xs text-black/50 mt-2 text-center"><InlineText value={p.caption} onSave={(v) => onUpdate({ caption: v })} /></figcaption>}
              </figure>
            ) : (
              <div className="bg-black/5 h-64 flex items-center justify-center text-sm text-black/50">No image set</div>
            )}
          </div>
        </section>
      );
    case "richtext":
      return (
        <section className="py-12" data-testid={`block-${block.id}`}>
          <div className="max-container max-w-3xl text-base md:text-lg leading-relaxed text-black/80 whitespace-pre-line">
            <InlineText value={p.body} multiline onSave={(v) => onUpdate({ body: v })} placeholder="Rich text content" />
          </div>
        </section>
      );
    default:
      return null;
  }
}
