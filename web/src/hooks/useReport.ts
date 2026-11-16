import { useEffect } from "react";
import { validateReport } from "../utils/schema";
import { useReportStore } from "../store/reportStore";
import demoReport from "../assets/demo-report.json";

/**
 * Loads the bundled demo report on mount if no report is loaded yet.
 */
export function useReport() {
  const { report, setReport } = useReportStore();

  useEffect(() => {
    if (report) return;
    const validated = validateReport(demoReport);
    if (validated) {
      setReport(validated);
    } else {
      console.error("Bundled demo report failed schema validation");
    }
  }, [report, setReport]);

  return report;
}
