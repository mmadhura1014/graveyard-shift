// In-browser JSON Schema validation using ajv.
// The report JSON never leaves the browser.

import Ajv2020 from "ajv/dist/2020";
import addFormats from "ajv-formats";
import type { Report } from "../types/report";

// Import the schema at build time — Vite handles JSON imports
import reportSchema from "../../../schema/report.schema.json";

const ajv = new Ajv2020({ allErrors: true });
addFormats(ajv);

// Compile once at module load
const _validate = ajv.compile(reportSchema);

/**
 * Validate an unknown value against the report schema.
 * Returns the typed Report on success, null on failure.
 */
export function validateReport(data: unknown): Report | null {
  const valid = _validate(data);
  if (!valid) return null;
  return data as unknown as Report;
}

export function validationErrors(): string[] {
  return (_validate.errors ?? []).map(
    (e) => `${e.instancePath || "/"} ${e.message}`
  );
}
