import { useEffect, useState } from "react";
import { useReportStore } from "../store/reportStore";
import { prefersReducedMotion } from "../utils/motion";

/**
 * True for ~1.4s after a cleanup command for `resourceId` was copied.
 * Subscribes to the store (an external system), so no state is set during render.
 * Skipped entirely under prefers-reduced-motion; the copy itself is unaffected.
 */
export function useVanishing(resourceId: string): boolean {
  const [vanishing, setVanishing] = useState(false);

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | undefined;
    const unsubscribe = useReportStore.subscribe((state, prev) => {
      if (state.exorcismNonce === prev.exorcismNonce) return;
      if (state.exorcisedResourceId !== resourceId || prefersReducedMotion()) return;
      setVanishing(true);
      clearTimeout(timer);
      timer = setTimeout(() => setVanishing(false), 1400);
    });
    return () => {
      unsubscribe();
      clearTimeout(timer);
    };
  }, [resourceId]);

  return vanishing;
}
