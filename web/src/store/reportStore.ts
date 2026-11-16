import { create } from "zustand";
import type { Report } from "../types/report";

export type ViewName = "graveyard" | "crypt" | "exorcism" | "about";

interface ReportState {
  report: Report | null;
  activeView: ViewName;
  // Exorcism animation trigger: shared so the Séance panel and the Exorcism
  // view's copy buttons can both animate the matching tombstone / card ghost.
  exorcisedResourceId: string | null;
  exorcismNonce: number;
  setReport: (r: Report) => void;
  clearReport: () => void;
  setActiveView: (v: ViewName) => void;
  exorcise: (resourceId: string) => void;
}

export const useReportStore = create<ReportState>((set) => ({
  report: null,
  activeView: "graveyard",
  exorcisedResourceId: null,
  exorcismNonce: 0,
  setReport: (r) => set({ report: r }),
  clearReport: () => set({ report: null }),
  setActiveView: (v) => set({ activeView: v }),
  exorcise: (resourceId) =>
    set((state) => ({
      exorcisedResourceId: resourceId,
      exorcismNonce: state.exorcismNonce + 1,
    })),
}));
