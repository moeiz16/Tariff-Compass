/**
 * Motion language "Bearing" (frontend/DESIGN.md §9). Everything animates transform, opacity or background-size;
 * with reduced motion every animation collapses to its final frame and no meaning is carried by motion alone.
 */
export function reducedMotion(): boolean {
  if (typeof window === "undefined" || !window.matchMedia) return true;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/** Run a WAAPI animation unless the person prefers reduced motion. */
export function animate(el: Element | undefined | null, frames: Keyframe[], opts: KeyframeAnimationOptions): Animation | null {
  if (!el || reducedMotion() || typeof (el as HTMLElement).animate !== "function") return null;
  return (el as HTMLElement).animate(frames, { fill: "both", ...opts });
}

export const EASE = {
  dock: "cubic-bezier(.2,.8,.2,1)",
  mark: "cubic-bezier(.3,0,.2,1)",
  lock: "cubic-bezier(.34,1.4,.64,1)",
  settle: "cubic-bezier(.25,.6,.3,1)",
};

/** Rise: children fade up 8 px in reading order. */
export function rise(container: Element | undefined | null, selector = "[data-rise]", stagger = 120): void {
  if (!container) return;
  container.querySelectorAll(selector).forEach((el, i) =>
    animate(el, [{ opacity: 0, transform: "translateY(8px)" }, { opacity: 1, transform: "none" }], {
      duration: 360,
      delay: i * stagger,
      easing: EASE.dock,
    }),
  );
}
