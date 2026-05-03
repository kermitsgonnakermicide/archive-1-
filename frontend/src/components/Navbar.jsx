import React, { useState, useEffect } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { Menu, X, Edit3 } from "lucide-react";
import { useApp } from "../context/AppContext";
import { LOGO_URL } from "../lib/brand";

const NAV_ITEMS = [
  { label: "Home", anchor: "#home" },
  { label: "What is SCALE", anchor: "#about" },
  { label: "Events", anchor: "#events" },
  { label: "Our Story", anchor: "#story" },
  { label: "Contact", anchor: "#contact" },
];

export default function Navbar() {
  const { user, logout, isAdmin, editMode, setEditMode, pages } = useApp();
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const onHome = location.pathname === "/";
  const navPages = (pages || []).filter((p) => p.show_in_nav && p.published);

  useEffect(() => {
    const on = () => setScrolled(window.scrollY > 24);
    on();
    window.addEventListener("scroll", on);
    return () => window.removeEventListener("scroll", on);
  }, []);

  const goTo = (anchor) => {
    setOpen(false);
    if (onHome) {
      const el = document.querySelector(anchor);
      if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
    } else {
      navigate("/" + anchor);
    }
  };

  const handleEvents = () => {
    setOpen(false);
    if (onHome) document.querySelector("#events")?.scrollIntoView({ behavior: "smooth" });
    else navigate("/#events");
  };

  return (
    <nav
      data-testid="navbar"
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled ? "navbar-solid shadow-lg" : "bg-[var(--scale-black)]"
      }`}
    >
      <div className="max-container flex items-center justify-between h-16 md:h-20">
        <Link to="/" data-testid="nav-logo" className="flex items-center gap-3 group">
          <img src={LOGO_URL} alt="SCALE" className="h-9 md:h-11 w-auto rounded-sm" />
          <span className="hidden md:inline font-serif font-bold text-white text-lg tracking-wider">SCALE</span>
        </Link>

        <div className="hidden lg:flex items-center gap-8">
          {NAV_ITEMS.map((it) => (
            <button
              key={it.anchor}
              onClick={() => goTo(it.anchor)}
              className="nav-link font-medium"
              data-testid={`nav-${it.anchor.replace('#', '')}`}
            >
              {it.label}
            </button>
          ))}
          {navPages.map((p) => (
            <Link
              key={p.id}
              to={`/p/${p.slug}`}
              className="nav-link font-medium"
              data-testid={`nav-page-${p.slug}`}
            >
              {p.nav_label || p.title}
            </Link>
          ))}
        </div>

        <div className="hidden lg:flex items-center gap-3">
          {isAdmin && (
            <button
              onClick={() => setEditMode(!editMode)}
              className={`text-sm flex items-center gap-2 px-3 py-1.5 border ${
                editMode ? "bg-[var(--scale-gold)] text-black border-[var(--scale-gold)]" : "border-white/30 text-white"
              }`}
              data-testid="nav-edit-mode-toggle"
            >
              <Edit3 size={14} /> {editMode ? "Editing" : "Edit"}
            </button>
          )}
          {user ? (
            <>
              {isAdmin && (
                <Link to="/admin" className="nav-link" data-testid="nav-admin-link">Admin</Link>
              )}
              <button onClick={() => { logout(); }} className="nav-link" data-testid="nav-logout-btn">Logout</button>
              <button onClick={handleEvents} data-testid="nav-events-btn" className="btn-gold text-sm">
                Explore Events
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="nav-link" data-testid="nav-login-link">Login</Link>
              <button onClick={handleEvents} data-testid="nav-events-btn" className="btn-gold text-sm">
                Explore Events
              </button>
            </>
          )}
        </div>

        <button
          className="lg:hidden text-white p-2"
          onClick={() => setOpen((s) => !s)}
          aria-label="menu"
          data-testid="nav-mobile-toggle"
        >
          {open ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>

      {open && (
        <div className="lg:hidden navbar-solid border-t border-white/10" data-testid="nav-mobile-panel">
          <div className="max-container py-4 flex flex-col gap-2">
            {NAV_ITEMS.map((it) => (
              <button
                key={it.anchor}
                onClick={() => goTo(it.anchor)}
                className="nav-link text-left py-2"
              >
                {it.label}
              </button>
            ))}
            {navPages.map((p) => (
              <Link
                key={p.id}
                to={`/p/${p.slug}`}
                onClick={() => setOpen(false)}
                className="nav-link py-2 text-left"
                data-testid={`nav-mobile-page-${p.slug}`}
              >
                {p.nav_label || p.title}
              </Link>
            ))}
            <div className="flex flex-col gap-2 pt-2 border-t border-white/10">
              {isAdmin && (
                <button
                  onClick={() => { setEditMode(!editMode); setOpen(false); }}
                  className="nav-link py-2 text-left flex items-center gap-2"
                >
                  <Edit3 size={14} /> {editMode ? "Stop Editing" : "Edit Mode"}
                </button>
              )}
              {user ? (
                <>
                  {isAdmin && (
                    <Link to="/admin" className="nav-link py-2" onClick={() => setOpen(false)}>Admin</Link>
                  )}
                  <button onClick={() => { logout(); setOpen(false); }} className="nav-link py-2 text-left">Logout</button>
                </>
              ) : (
                <Link to="/login" className="nav-link py-2" onClick={() => setOpen(false)}>Login</Link>
              )}
              <button onClick={handleEvents} className="btn-gold text-sm w-full justify-center mt-2">Explore Events</button>
            </div>
          </div>
        </div>
      )}
    </nav>
  );
}
