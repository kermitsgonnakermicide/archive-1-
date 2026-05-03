import React from "react";
import { useApp } from "../context/AppContext";
import { ArrowRight } from "lucide-react";
import Editable from "./Editable";

export default function UpcomingBanner() {
  const { content } = useApp();
  const scrollTo = (id) => document.querySelector(id)?.scrollIntoView({ behavior: "smooth" });

  return (
    <section className="crimson-section py-10 md:py-14" data-testid="upcoming-banner">
      <div className="max-container flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="reveal">
          <div className="text-[10px] tracking-[0.3em] uppercase font-bold text-[var(--scale-goldlight)]">
            <Editable field="upcoming_event_date" value={content?.upcoming_event_date} />
          </div>
          <Editable
            as="h3"
            field="upcoming_event_title"
            value={content?.upcoming_event_title}
            className="font-serif font-black text-2xl md:text-4xl text-white mt-2 block"
          />
          <Editable
            as="p"
            field="upcoming_event_desc"
            value={content?.upcoming_event_desc}
            multiline
            className="text-white/80 mt-2 max-w-2xl text-sm md:text-base block"
          />
        </div>
        <button className="btn-gold reveal" onClick={() => scrollTo("#events")} data-testid="upcoming-cta">
          View Details <ArrowRight size={16} />
        </button>
      </div>
    </section>
  );
}
