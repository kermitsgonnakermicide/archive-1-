import React from "react";
import Hero from "../components/Hero";
import FieldsStrip from "../components/FieldsStrip";
import Pillars from "../components/Pillars";
import WhatIsScale from "../components/WhatIsScale";
import EventsSection from "../components/EventsSection";
import UpcomingBanner from "../components/UpcomingBanner";
import StorySection from "../components/StorySection";
import ContactSection from "../components/ContactSection";
import { useApp } from "../context/AppContext";

export default function HomePage() {
  const { loading, content } = useApp();

  if (loading || !content) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--scale-darkred)] text-white">
        <div className="font-serif text-xl">Loading SCALE…</div>
      </div>
    );
  }

  return (
    <div data-testid="home-page">
      <Hero />
      <FieldsStrip />
      <Pillars />
      <UpcomingBanner />
      <WhatIsScale />
      <EventsSection />
      <StorySection />
      <ContactSection />
    </div>
  );
}
