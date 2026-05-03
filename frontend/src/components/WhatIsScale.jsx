import React from "react";
import { useApp } from "../context/AppContext";
import Editable from "./Editable";
import { Plus, Trash2 } from "lucide-react";

export default function WhatIsScale() {
  const { content, saveContentPatch, editing } = useApp();
  const fields = content?.fields_strip || [];
  const why = content?.why_scale_items || [];

  const addWhy = async () => {
    const next = [...why, { title: "New reason", desc: "Description here" }];
    await saveContentPatch({ why_scale_items: next });
  };
  const removeWhy = async (idx) => {
    const next = why.filter((_, i) => i !== idx);
    await saveContentPatch({ why_scale_items: next });
  };
  const updateWhy = async (idx, field, val) => {
    const next = why.map((it, i) => (i === idx ? { ...it, [field]: val } : it));
    await saveContentPatch({ why_scale_items: next });
  };

  return (
    <section id="about" className="bg-[var(--scale-offwhite)] py-16 md:py-24" data-testid="about-section">
      <div className="max-container">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
          <div className="lg:col-span-5 reveal">
            <div className="eyebrow">What is SCALE</div>
            <h2 className="font-serif font-black text-3xl md:text-5xl leading-[1.1]">
              India's first serious national platform for high school business talent.
            </h2>
          </div>
          <div className="lg:col-span-7 reveal">
            <Editable
              as="p"
              field="about_paragraph"
              value={content?.about_paragraph}
              multiline
              className="text-base md:text-lg leading-relaxed text-black/80 block"
              testId="about-paragraph"
            />

            <div className="mt-8 grid grid-cols-2 md:grid-cols-4 gap-3">
              {fields.map((f, i) => (
                <div key={i} className="bg-white border border-black/10 p-4">
                  <div className="text-[10px] tracking-[0.28em] uppercase text-[var(--scale-crimson)] font-bold">Field 0{i + 1}</div>
                  <div className="font-serif font-bold mt-1 text-lg">{f}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-16">
          <div className="flex items-center justify-between flex-wrap gap-3 reveal">
            <Editable as="div" field="why_eyebrow" value={content?.why_eyebrow} className="eyebrow block" />
            {editing && (
              <button onClick={addWhy} className="btn-outline-dark text-xs"><Plus size={12} /> Add reason</button>
            )}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-0 mt-4 border-t border-black/10">
            {why.map((item, i) => (
              <div
                key={i}
                className="relative py-8 px-0 md:px-8 border-b md:border-b-0 md:border-r border-black/10 last:border-r-0 reveal"
                data-testid={`why-item-${i}`}
              >
                {editing && (
                  <button onClick={() => removeWhy(i)} className="absolute top-2 right-2 bg-black/70 text-white p-1 rounded-full">
                    <Trash2 size={10} />
                  </button>
                )}
                <div className="text-[var(--scale-crimson)] font-serif font-black text-3xl mb-3">0{i + 1}</div>
                <Editable
                  as="h3"
                  value={item.title}
                  className="font-serif font-bold text-xl mb-2 block"
                  onSave={(v) => updateWhy(i, "title", v)}
                />
                <Editable
                  as="p"
                  value={item.desc}
                  multiline
                  className="text-sm text-black/75 leading-relaxed block"
                  onSave={(v) => updateWhy(i, "desc", v)}
                />
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
