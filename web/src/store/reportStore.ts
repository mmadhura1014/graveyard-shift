import { create } from "zustand";
import type { Report } from "../types/report";

export type ViewName = "graveyard" | "crypt" | "exorcism" | "about";

interface ReportState {
  report: Report | null;
  activeView: ViewName;
  setReport: (r: Report) => void;
  clearReport: () => void;
  setActiveView: (v: ViewName) => void;
}

export const useReportStore = create<ReportState>((set) => ({
  report: null,
  activeView: "graveyard",
  setReport: (r) => set({ report: r }),
  clearReport: () => set({ report: null }),
  setActiveView: (v) => set({ activeView: v }),
}));
