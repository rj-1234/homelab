import gsap from "gsap";

// Shared across components so each doesn't register its own matchMedia
// handler. Read `.reduceMotion` at animation-trigger time.
export const motionState = { reduceMotion: false };

gsap.matchMedia().add("(prefers-reduced-motion: reduce)", () => {
  motionState.reduceMotion = true;
  return () => {
    motionState.reduceMotion = false;
  };
});
