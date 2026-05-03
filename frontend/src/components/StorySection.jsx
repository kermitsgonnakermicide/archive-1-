import React from "react";
import { useApp } from "../context/AppContext";
import Editable from "./Editable";
import { LOGO_URL } from "../lib/brand";

export default function StorySection() {
  const { content } = useApp();
  return (
    <section id="story" className="bg-[var(--scale-cream)] py-16 md:py-24" data-testid="story-section">
      <div className="max-container grid grid-cols-1 lg:grid-cols-12 gap-10 items-start">
        <div className="lg:col-span-7 reveal">
          <Editable as="div" field="story_eyebrow" value={content?.story_eyebrow} className="eyebrow block" />
          <Editable
            as="h2"
            field="story_headline"
            value={content?.story_headline}
            multiline
            className="font-serif font-black text-3xl md:text-5xl leading-[1.1] mb-5 block"
          />
          <Editable
            as="p"
            field="founder_story"
            value={content?.founder_story}
            multiline
            className="text-base md:text-lg text-black/80 leading-relaxed block"
            testId="founder-story"
          />

          <div className="gold-left mt-10 max-w-2xl" data-testid="vision-quote">
            <Editable as="div" field="vision_eyebrow" value={content?.vision_eyebrow} className="eyebrow-gold block" />
            <span className="font-serif italic text-lg md:text-xl leading-snug block">
              "<Editable field="vision_quote" value={content?.vision_quote} multiline />"
            </span>
          </div>
        </div>

        <div className="lg:col-span-5 reveal">
          <div className="crimson-section p-6 md:p-8 relative" data-testid="founder-card">
            <img src={LOGO_URL} alt="SCALE" className="w-full max-w-sm mx-auto mb-6 rounded-sm" />
            <div className="h-px bg-[var(--scale-gold)] my-4 opacity-70" />
            <div className="text-[10px] tracking-[0.28em] uppercase text-[var(--scale-goldlight)] font-bold">Founder</div>
            <Editable
              as="div"
              field="founder_name"
              value={content?.founder_name}
              className="font-serif font-black text-2xl mt-1 text-white"
            />
            <Editable
              as="div"
              field="founder_title"
              value={content?.founder_title}
              className="text-white/80 text-sm mt-1"
            />
          </div>
        </div>
      </div>
    </section>
  );
}
