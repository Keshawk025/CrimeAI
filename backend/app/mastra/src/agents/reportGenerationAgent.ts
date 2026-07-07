/**
 * src/agents/reportGenerationAgent.ts
 * ─────────────────────────────────────
 * ReportGenerationAgent — compiles the final investigation report.
 *
 * Terminal step of the workflow. Report persistence added in future tasks.
 */

import { createStep } from "@mastra/core/workflows";
import { z } from "zod";
import { logger } from "../logger.js";

export const reportGenerationAgentStep = createStep({
  id: "report-generation-agent",

  description:
    "Compiles all intermediate outputs into a structured investigation " +
    "report and persists it via ReportStorageTool.",

  inputSchema: z.object({
    caseId: z.string(),
    recommendations: z.array(
      z.object({
        priority: z.enum(["high", "medium", "low"]),
        action: z.string(),
        rationale: z.string(),
      }),
    ),
    message: z.string(),
  }),

  outputSchema: z.object({
    caseId: z.string(),
    reportGenerated: z.boolean(),
    reportId: z.string().optional(),
    summary: z.string(),
  }),

  execute: async ({ inputData }) => {
    logger.info(
      `[ReportGenerationAgent] Generating report for case ${inputData.caseId}`,
    );

    // ── Placeholder: no report generation yet ─────────────────
    // Future: call ReportStorageTool to persist structured report

    return {
      caseId: inputData.caseId,
      reportGenerated: false,
      summary:
        "ReportGenerationAgent placeholder — awaiting full pipeline integration",
    };
  },
});
