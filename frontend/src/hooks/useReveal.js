import { useEffect } from "react";

export function useReveal(dep) {
  useEffect(() => {
    const observe = () => {
      const els = document.querySelectorAll(".reveal:not(.in-view)");
      if (!els.length) return;
      const io = new IntersectionObserver(
        (entries) => {
          entries.forEach((e) => {
            if (e.isIntersecting) {
              e.target.classList.add("in-view");
              io.unobserve(e.target);
            }
          });
        },
        { threshold: 0.05, rootMargin: "0px 0px -40px 0px" }
      );
      els.forEach((el) => io.observe(el));
      return io;
    };

    let io = observe();

    // Re-observe after small delay in case new elements mount
    const t1 = setTimeout(() => { io && io.disconnect(); io = observe(); }, 400);
    const t2 = setTimeout(() => {
      // Fallback: reveal anything still hidden in viewport on slow load
      document.querySelectorAll(".reveal:not(.in-view)").forEach((el) => {
        const r = el.getBoundingClientRect();
        if (r.top < window.innerHeight && r.bottom > 0) el.classList.add("in-view");
      });
    }, 1200);

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      io && io.disconnect();
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dep]);
}
