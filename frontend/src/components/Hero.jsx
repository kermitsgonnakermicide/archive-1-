import React from "react";
import { ArrowRight } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useApp } from "../context/AppContext";
import { LOGO_URL } from "../lib/brand";
import Editable from "./Editable";

function highlightNextGeneration(text) {
  if (!text) return text;
  const re = /(next generation)/i;
  const parts = text.split(re);
  return parts.map((p, i) =>
    re.test(p) ? (
      <em key={i} className="italic text-[var(--scale-gold)] font-black" style={{ fontFamily: "'Playfair Display', Georgia, serif" }}>
        {p}
      </em>
    ) : (
      <React.Fragment key={i}>{p}</React.Fragment>
    )
  );
}

export default function Hero() {
  const { content } = useApp();
  const navigate = useNavigate();
  const scrollTo = (id) => document.querySelector(id)?.scrollIntoView({ behavior: "smooth" });

  return (
    <section id="home" className="hero-bg pt-24 md:pt-28 pb-16 md:pb-24" data-testid="hero-section">
      <div className="max-container relative grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-16 items-center">
        <div className="lg:col-span-7 text-white">
          <span className="label-badge reveal" data-testid="hero-badge">
            <Editable field="hero_label" value={content?.hero_label} />
          </span>

          <Editable
            as="h1"
            field="hero_headline"
            value={content?.hero_headline}
            multiline
            className="mt-6 font-serif font-black text-4xl sm:text-5xl lg:text-6xl xl:text-7xl leading-[1.05] tracking-tight reveal block"
            testId="hero-headline"
            renderValue={(txt) => highlightNextGeneration(txt)}
          />

          <Editable
            as="p"
            field="hero_subtext"
            value={content?.hero_subtext}
            multiline
            className="mt-6 text-base md:text-lg text-white/80 max-w-2xl leading-relaxed reveal block"
            testId="hero-subtext"
          />

          <div className="mt-8 flex flex-wrap gap-3 reveal">
            <button
              className="btn-gold"
              onClick={() => scrollTo("#events")}
              data-testid="hero-events-btn"
            >
              {content?.hero_cta_primary || "Explore Events"} <ArrowRight size={16} />
            </button>
            <button
              className="btn-outline-light"
              onClick={() => scrollTo("#story")}
              data-testid="hero-story-btn"
            >
              {content?.hero_cta_secondary || "Our Story"}
            </button>
          </div>

          <div className="mt-10 flex items-center gap-3 text-xs uppercase tracking-[0.28em] text-white/60 reveal">
            <span className="hr-gold" />
            <Editable field="hero_ticker" value={content?.hero_ticker} />
          </div>
        </div>

        <div className="lg:col-span-5 flex justify-center lg:justify-end">
          <div className="relative reveal">
            <div className="absolute -inset-3 border-2 border-[var(--scale-gold)]/40 rotate-1" />
            <img
              src={LOGO_URL}
              alt="SCALE logo"
              className="relative w-full max-w-md lg:max-w-lg shadow-2xl rounded-sm"
              data-testid="hero-logo-image"
            />
          </div>
        </div>
      </div>
    </section>
  );
}
