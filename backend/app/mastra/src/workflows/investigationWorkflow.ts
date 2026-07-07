/**
 * src/workflows/investigationWorkflow.ts
 * ────────────────────────────────────────
 * InvestigationWorkflow — the primary case analysis pipeline.
 *
 * Orchestration sequence:
 *
 *   InvestigationAgent
 *         ↓
 *   EntityExtractionAgent
 *         ↓
 *   SimilarCaseAgent
 *         ↓
 *   RecommendationAgent
 *         ↓
 *   ReportGenerationAgent
 *
 * Each step is a placeholder with full typed schemas.
 * Business logic is filled in future tasks.
 */

import { createWorkflow } from "@mastra/core/workflows";
import { z } from "zod";
import { entityExtractionAgentStep } from "../agents/entityExtractionAgent.js";
import { investigationAgentStep } from "../agents/investigationAgent.js";
import { recommendationAgentStep } from "../agents/recommendationAgent.js";
import { reportGenerationAgentStep } from "../agents/reportGenerationAgent.js";
import { similarCaseAgentStep } from "../agents/similarCaseAgent.js";
import { logger } from "../logger.js";

export const investigationWorkflow = createWorkflow({
  id: "investigation-workflow",

  description:
    "End-to-end investigation pipeline: validates input → extracts entities → " +
    "finds similar cases → generates recommendations → produces a final report.",

  inputSchema: z.object({
    caseId: z
      .string()
      .min(1)
      .describe("Unique identifier for the investigation case"),
    rawInput: z
      .string()
      .optional()
      .describe("Raw FIR text or description (optional at this stage)"),
  }),

  outputSchema: z.object({
    caseId: z.string(),
    reportGenerated: z.boolean(),
    reportId: z.string().optional(),
    summary: z.string(),
  }),
})
  .then(investigationAgentStep)
  .then(entityExtractionAgentStep)
  .then(similarCaseAgentStep)
  .then(recommendationAgentStep)
  .then(reportGenerationAgentStep)
  .commit();

logger.info(
  `[InvestigationWorkflow] Workflow '${investigationWorkflow.id}' registered with 5 steps.`,
);
