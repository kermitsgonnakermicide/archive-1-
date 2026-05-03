import React, { useState, useEffect, useRef } from "react";
import { useApp } from "../context/AppContext";
import { Pencil, Check, X } from "lucide-react";

/**
 * Editable wrapper. When admin is in edit mode, click to edit text.
 * - field: key in content object to update
 * - as: 'h1' | 'p' | 'span' etc.
 * - multiline: render textarea
 */
export default function Editable({
  field,
  value,
  as: As = "span",
  multiline = false,
  className = "",
  onSave,
  placeholder = "",
  testId,
  renderValue,
}) {
  const { editing, saveContentPatch } = useApp();
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState(value || "");
  const ref = useRef(null);

  useEffect(() => { setDraft(value || ""); }, [value]);
  useEffect(() => {
    if (open && ref.current) {
      ref.current.focus();
      ref.current.select?.();
    }
  }, [open]);

  const save = async () => {
    if (onSave) await onSave(draft);
    else if (field) await saveContentPatch({ [field]: draft });
    setOpen(false);
  };

  if (!editing) {
    return <As className={className} data-testid={testId}>{renderValue ? renderValue(value) : (value || placeholder)}</As>;
  }

  if (open) {
    return (
      <span className="relative inline-block w-full">
        {multiline ? (
          <textarea
            ref={ref}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            rows={Math.min(10, Math.max(2, (draft || "").split("\n").length + 1))}
            className="w-full bg-white text-black border-2 border-[var(--scale-gold)] p-2 outline-none font-sans text-base"
          />
        ) : (
          <input
            ref={ref}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            className="w-full bg-white text-black border-2 border-[var(--scale-gold)] p-2 outline-none font-sans"
          />
        )}
        <span className="absolute -top-3 right-0 flex gap-1 z-30">
          <button onClick={save} className="bg-[var(--scale-crimson)] text-white p-1 shadow-md" title="Save"><Check size={14} /></button>
          <button onClick={() => { setDraft(value || ""); setOpen(false); }} className="bg-black/80 text-white p-1 shadow-md" title="Cancel"><X size={14} /></button>
        </span>
      </span>
    );
  }

  return (
    <As
      className={`${className} relative cursor-pointer ring-1 ring-dashed ring-[var(--scale-gold)]/60 hover:ring-2 hover:ring-[var(--scale-gold)] inline-block`}
      onClick={() => setOpen(true)}
      data-testid={testId}
    >
      {renderValue ? renderValue(value) : (value || placeholder)}
      <span className="absolute -top-3 -right-2 bg-[var(--scale-gold)] text-black p-0.5 rounded-full shadow-sm">
        <Pencil size={10} />
      </span>
    </As>
  );
}
