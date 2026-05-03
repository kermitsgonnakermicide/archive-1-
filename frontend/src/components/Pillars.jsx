import React from "react";
import { useApp } from "../context/AppContext";
import Editable from "./Editable";
import { Plus, Trash2 } from "lucide-react";

export default function Pillars() {
  const { content, saveContentPatch, editing } = useApp();
  const pillars = content?.pillars || [];

  const update = async (i, field, val) => {
    const next = pillars.map((p, idx) => (idx === i ? { ...p, [field]: val } : p));
    await saveContentPatch({ pillars: next });
  };
  const add = async () => {
    if (pillars.length >= 6) return;
    await saveContentPatch({ pillars: [...pillars, { title: "NEW", desc: "Add description" }] });
  };
  const remove = async (i) => {
    await saveContentPatch({ pillars: pillars.filter((_, idx) => idx !== i) });
  };

  const cols = pillars.length === 4 ? "lg:grid-cols-4" : pillars.length === 3 ? "lg:grid-cols-3" : pillars.length === 2 ? "lg:grid-cols-2" : "lg:grid-cols-4";

  return (
    <section className="dark-red-section py-16 md:py-24" data-testid="pillars-section">
      <div className="max-container relative">
        <div className="max-w-3xl reveal flex items-end justify-between gap-4 flex-wrap">
          <div>
            <Editable as="div" field="pillars_eyebrow" value={content?.pillars_eyebrow} className="eyebrow-gold block" />
            <Editable
              as="h2"
              field="pillars_headline"
              value={content?.pillars_headline}
              multiline
              className="font-serif font-bold text-3xl md:text-5xl leading-tight block"
            />
          </div>
          {editing && (
            <button onClick={add} className="btn-outline-light text-xs"><Plus size={12} /> Add pillar</button>
          )}
        </div>
        <div className={`mt-10 md:mt-14 grid grid-cols-1 sm:grid-cols-2 ${cols} gap-0 border border-white/10`}>
          {pillars.map((p, i) => (
            <div key={i} className="pillar-card reveal relative" data-testid={`pillar-${i}`}>
              {editing && (
                <button onClick={() => remove(i)} className="absolute top-2 right-2 bg-black/60 text-white p-1 rounded-full">
                  <Trash2 size={10} />
                </button>
              )}
              <div className="text-xs tracking-[0.3em] text-[var(--scale-goldlight)] font-bold mb-3">0{i + 1}</div>
              <Editable
                as="h3"
                value={p.title}
                className="font-serif font-black text-3xl md:text-4xl mb-3 block text-white"
                onSave={(v) => update(i, "title", v)}
              />
              <Editable
                as="p"
                value={p.desc}
                multiline
                className="text-white/75 leading-relaxed text-sm block"
                onSave={(v) => update(i, "desc", v)}
              />
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
