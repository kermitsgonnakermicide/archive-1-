import React from "react";
import { useApp } from "../context/AppContext";
import Editable from "./Editable";

export default function FieldsStrip() {
  const { content, saveContentPatch, editing } = useApp();
  const fields = content?.fields_strip || [];

  const update = async (i, val) => {
    const next = fields.map((f, idx) => (idx === i ? val : f));
    await saveContentPatch({ fields_strip: next });
  };

  return (
    <section className="bg-white border-y border-black/5" data-testid="fields-strip">
      <div className="max-container grid grid-cols-2 md:grid-cols-4">
        {fields.map((f, i) => (
          <div
            key={i}
            className="crimson-top px-5 py-8 md:py-10 border-r border-black/5 last:border-r-0 reveal"
            data-testid={`field-${i}`}
          >
            <div className="text-[10px] tracking-[0.28em] uppercase text-[var(--scale-crimson)] font-bold mb-2">0{i + 1}</div>
            <Editable
              as="h3"
              value={f}
              className="font-serif font-bold text-xl md:text-2xl block"
              onSave={(v) => update(i, v)}
            />
          </div>
        ))}
      </div>
    </section>
  );
}
