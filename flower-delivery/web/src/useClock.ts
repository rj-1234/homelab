import { useEffect, useRef, useState } from "react";

export function usePrefersReducedMotion(): boolean {
  const [reduced] = useState(
    () => typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
  return reduced;
}

export function useClock(active: boolean): number {
  const [clock, setClock] = useState(() => performance.now() / 1000);
  const rafRef = useRef<number>();
  useEffect(() => {
    if (!active) return;
    const loop = () => {
      setClock(performance.now() / 1000);
      rafRef.current = requestAnimationFrame(loop);
    };
    rafRef.current = requestAnimationFrame(loop);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [active]);
  return clock;
}
