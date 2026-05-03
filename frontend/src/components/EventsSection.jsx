import React from "react";
import { useNavigate } from "react-router-dom";
import { useApp } from "../context/AppContext";
import Editable from "./Editable";
import { ArrowRight, Plus, Trash2 } from "lucide-react";
import { eventsApi } from "../lib/api";
import { toast } from "sonner";

export default function EventsSection() {
  const { content, events, refreshEvents, editing, isAdmin } = useApp();
  const navigate = useNavigate();

  const addEvent = async () => {
    try {
      await eventsApi.create({
        title: "New Event",
        description: "Short description",
        about: "Long-form about section. Click in edit mode on the event detail page to update.",
        status: "coming_soon",
        cta_label: "Event Details",
        date: "TBA",
        location: "TBA",
        price_inr: 500,
        order: events.length + 1,
      });
      toast.success("Event added.");
      refreshEvents();
    } catch { toast.error("Add failed."); }
  };

  const removeEvent = async (id) => {
    if (!window.confirm("Delete this event?")) return;
    await eventsApi.remove(id);
    toast.success("Event deleted.");
    refreshEvents();
  };

  return (
    <section id="events" className="bg-white py-16 md:py-24" data-testid="events-section">
      <div className="max-container">
        <div className="max-w-3xl reveal">
          <Editable as="div" field="events_eyebrow" value={content?.events_eyebrow} className="eyebrow block" />
          <Editable
            as="h2"
            field="events_headline"
            value={content?.events_headline}
            multiline
            className="font-serif font-black text-3xl md:text-5xl leading-[1.1] block"
          />
        </div>

        <div className="mt-12 grid grid-cols-1 md:grid-cols-2 gap-6">
          {events.map((e) => {
            const isLive = e.status === "live";
            return (
              <div
                key={e.id}
                className={`relative border p-8 reveal ${isLive ? "border-[var(--scale-crimson)]" : "border-black/15"}`}
                data-testid={`event-card-${e.id}`}
              >
                {editing && (
                  <button
                    onClick={() => removeEvent(e.id)}
                    className="absolute top-3 right-3 bg-black/80 text-white p-1 rounded-full"
                    title="Delete event"
                  >
                    <Trash2 size={12} />
                  </button>
                )}
                <div className="flex items-center gap-2 mb-3">
                  <span
                    className={`text-[10px] tracking-[0.28em] uppercase font-bold ${
                      isLive ? "text-[var(--scale-crimson)]" : "text-[var(--scale-gold)]"
                    }`}
                  >
                    {isLive ? "● Live" : "Coming Soon"}
                  </span>
                  {e.date && <span className="text-xs text-black/50">· {e.date}</span>}
                </div>
                <h3 className="font-serif font-black text-2xl md:text-3xl mb-3">{e.title}</h3>
                <p className="text-sm text-black/75 leading-relaxed mb-6 min-h-[80px]">{e.description}</p>
                <button
                  onClick={() => navigate(`/events/${e.id}`)}
                  className={`text-sm ${isLive ? "btn-crimson" : "btn-outline-dark"}`}
                  data-testid={`event-details-btn-${e.id}`}
                >
                  Event Details <ArrowRight size={14} />
                </button>
              </div>
            );
          })}
          {editing && (
            <button
              onClick={addEvent}
              className="border-2 border-dashed border-[var(--scale-gold)] p-8 flex items-center justify-center gap-2 text-[var(--scale-crimson)] font-semibold hover:bg-[var(--scale-cream)]"
              data-testid="add-event-card"
            >
              <Plus size={16} /> Add new event
            </button>
          )}
        </div>

        <div className="mt-8 bg-[var(--scale-cream)] border-l-4 border-[var(--scale-gold)] px-5 py-4 reveal">
          <p className="font-serif italic text-base text-black/80" data-testid="competitions-teaser">
            <Editable field="competitions_teaser" value={content?.competitions_teaser} multiline />
          </p>
        </div>
      </div>
    </section>
  );
}
