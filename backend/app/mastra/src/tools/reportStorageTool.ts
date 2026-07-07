/**
 * src/tools/reportStorageTool.ts
 * ────────────────────────────────
 * ReportStorageTool — persists generated investigation reports.
 *
 * Placeholder. PostgreSQL persistence via FastAPI backend added in a future task.
 */

import { createTool } from "@mastra/core/tools";
import { z } from "zod";

export const reportStorageTool = createTool({
  id: "report-storage",

  description:
    "Persists a structured investigation report to the CrimeMind database " +
    "via the FastAPI backend and returns the generated report ID.",

  inputSchema: z.object({
    caseId: z.string().describe("The case this report belongs to"),
    reportContent: z
      .string()
      .describe("Markdown-formatted report content"),
    recommendations: z
      .array(
        z.object({
          priority: z.enum(["high", "medium", "low"]),
          action: z.string(),
          rationale: z.string(),
        }),
      )
      .default([])
      .describe("Structured recommendations to store alongside the report"),
    generatedAt: z
      .string()
      .datetime()
      .optional()
      .describe("ISO-8601 timestamp (defaults to now)"),
  }),

  outputSchema: z.object({
    reportId: z.string(),
    storedAt: z.string().datetime(),
    success: z.boolean(),
  }),

  execute: async ({ context }) => {
    // ── Placeholder: backend storage not wired yet ─────────────
    // Future: POST to FastAPI /api/v1/reports endpoint

    console.warn(
      "[ReportStorageTool] Placeholder — storage not implemented yet.",
    );

    return {
      reportId: `placeholder-${Date.now()}`,
      storedAt: new Date().toISOString(),
      success: false,
    };
  },
});
