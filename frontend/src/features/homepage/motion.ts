// Motion on the homepage (design "Animations"): every motion finishes within 1.2 s, and with
// prefers-reduced-motion nothing moves: each element shows its end state as soon as its
// trigger fires.
import { onBeforeUnmount, onMounted, ref, type Ref } from "vue";

export function prefersReducedMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

/** Timers that are cleared when the component goes away. */
export function useTimers(): {
  later: (fn: () => void, ms: number) => void;
  clear: () => void;
} {
  const timers = new Set<ReturnType<typeof setTimeout>>();
  function later(fn: () => void, ms: number): void {
    const id = setTimeout(() => {
      timers.delete(id);
      fn();
    }, ms);
    timers.add(id);
  }
  function clear(): void {
    for (const id of timers) clearTimeout(id);
    timers.clear();
  }
  onBeforeUnmount(clear);
  return { later, clear };
}

/** Becomes true once, when `share` of the element is in view (or at once without observers). */
export function useSeenOnce(
  target: Ref<Element | null>,
  share = 0.3,
): Ref<boolean> {
  const seen = ref(false);
  let observer: IntersectionObserver | null = null;
  onMounted(() => {
    if (typeof IntersectionObserver === "undefined" || !target.value) {
      seen.value = true;
      return;
    }
    observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          seen.value = true;
          observer?.disconnect();
        }
      },
      { threshold: share },
    );
    observer.observe(target.value);
  });
  onBeforeUnmount(() => observer?.disconnect());
  return seen;
}
