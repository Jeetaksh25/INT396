"use client";

import { createContext, useContext, useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import gsap from "gsap";
import type Lenis from "lenis";

type MotionContextValue = {
  reducedMotion: boolean;
  scrollTo: (target: number | string, offset?: number) => void;
};

const MotionContext = createContext<MotionContextValue>({
  reducedMotion: false,
  scrollTo: () => {},
});

export function useMotion() {
  return useContext(MotionContext);
}

export function MotionProvider({ children }: { children: React.ReactNode }) {
  const [reducedMotion, setReducedMotion] = useState(false);
  const [lenis, setLenis] = useState<Lenis | null>(null);
  const pathname = usePathname();
  const firstRender = useRef(true);

  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    const applyPreference = () => setReducedMotion(query.matches);
    applyPreference();
    query.addEventListener("change", applyPreference);

    if (query.matches) {
      return () => query.removeEventListener("change", applyPreference);
    }

    let instance: Lenis | null = null;
    let tick: ((time: number) => void) | null = null;
    let cancelled = false;

    import("lenis").then(({ default: LenisConstructor }) => {
      if (cancelled) {
        return;
      }
      const lenisInstance = new LenisConstructor({
        duration: 1.05,
        easing: (t: number) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
        smoothWheel: true,
        touchMultiplier: 1.4,
      });
      instance = lenisInstance;
      tick = (time: number) => lenisInstance.raf(time * 1000);
      gsap.ticker.add(tick);
      gsap.ticker.lagSmoothing(0);
      setLenis(lenisInstance);
    });

    return () => {
      cancelled = true;
      if (tick) {
        gsap.ticker.remove(tick);
      }
      instance?.destroy();
      setLenis(null);
      query.removeEventListener("change", applyPreference);
    };
  }, []);

  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    if (lenis) {
      lenis.scrollTo(0, { immediate: true });
    } else {
      window.scrollTo(0, 0);
    }
  }, [pathname, lenis]);

  const scrollTo = (target: number | string, offset = 0) => {
    if (lenis) {
      lenis.scrollTo(target, { offset, duration: 1.1 });
      return;
    }
    if (typeof target === "number") {
      window.scrollTo({ top: target + offset, behavior: "smooth" });
      return;
    }
    const element = document.querySelector(target);
    if (element) {
      const top = element.getBoundingClientRect().top + window.scrollY + offset;
      window.scrollTo({ top, behavior: "smooth" });
    }
  };

  return (
    <MotionContext.Provider value={{ reducedMotion, scrollTo }}>
      {children}
    </MotionContext.Provider>
  );
}
