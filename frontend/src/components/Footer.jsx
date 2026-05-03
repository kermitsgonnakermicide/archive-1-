import React from "react";
import { useApp } from "../context/AppContext";
import { LOGO_URL } from "../lib/brand";
import Editable from "./Editable";

export default function Footer() {
  const { content } = useApp();
  return (
    <footer className="footer-black" data-testid="footer">
      <div className="max-container py-10 md:py-12 grid grid-cols-1 md:grid-cols-3 items-center gap-6">
        <div className="flex items-center gap-3 justify-center md:justify-start">
          <img src={LOGO_URL} alt="SCALE" className="h-10 w-auto rounded-sm" />
          <span className="font-serif font-bold text-white text-xl">SCALE</span>
        </div>
        <div className="text-center">
          <span className="italic text-[var(--scale-goldlight)] font-serif text-lg">
            "<Editable field="footer_tagline" value={content?.footer_tagline} testId="footer-tagline" />"
          </span>
        </div>
        <div className="text-center md:text-right text-xs text-white/60 tracking-wider uppercase">
          © {new Date().getFullYear()} SCALE India · All rights reserved
        </div>
      </div>
    </footer>
  );
}
