import { useRef, useState } from "react";
import type { DragEvent, ChangeEvent } from "react";
import { validateReport, validationErrors } from "../utils/schema";
import { useReportStore } from "../store/reportStore";

export function FileDropZone() {
  const { setReport } = useReportStore();
  const [dragging, setDragging] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  function showToast(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(null), 5000);
  }

  function handleFile(file: File) {
    if (!file.name.endsWith(".json")) {
      showToast("Please drop a .json file.");
      return;
    }
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = JSON.parse(e.target?.result as string);
        const report = validateReport(data);
        if (report) {
          setReport(report);
        } else {
          const errs = validationErrors().slice(0, 3).join("; ");
          showToast(`Invalid report: ${errs}`);
        }
      } catch {
        showToast("Could not parse JSON file.");
      }
    };
    reader.readAsText(file);
  }

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }

  function onChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  }

  return (
    <div className="filedrop-wrapper">
      <div
        className={`filedrop${dragging ? " filedrop--over" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        role="button"
        tabIndex={0}
        aria-label="Drop a report.json file here or click to open"
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") inputRef.current?.click(); }}
      >
        <span className="filedrop-icon" aria-hidden="true">📂</span>
        <span>Drop your <code>report.json</code> here</span>
        <span className="filedrop-sub">Processed locally — never uploaded anywhere</span>
      </div>

      <input
        ref={inputRef}
        type="file"
        accept=".json"
        style={{ display: "none" }}
        onChange={onChange}
        aria-hidden="true"
      />

      {toast && (
        <div className="toast" role="alert" aria-live="assertive">
          {toast}
        </div>
      )}
    </div>
  );
}
