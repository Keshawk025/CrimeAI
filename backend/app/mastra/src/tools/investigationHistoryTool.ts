/**
 * src/tools/investigationHistoryTool.ts
 * ───────────────────────────────────────
 * InvestigationHistoryTool — retrieves a case's prior investigation activity.
 *
 * Placeholder. PostgreSQL query via FastAPI added in a future task.
 */

import { createTool } from "@mastra/core/tools";
import { z } from "zod";

export const investigationHistoryTool = createTool({
  id: "investigation-history",

  description:
    "Retrieves the full investigation history for a case including prior " +
    "runs, generated reports, and analyst notes from the CrimeMind database.",

  inputSchema: z.object({
    caseId: z.string().describe("The case to retrieve history for"),
    limit: z
      .number()
      .int()
      .min(1)
      .max(100)
      .default(10)
      .describe("Maximum number of history entries to return"),
  }),

  outputSchema: z.object({
    caseId: z.string(),
    history: z.array(
      z.object({
        runId: z.string(),
        status: z.string(),
        startedAt: z.string().datetime(),
        completedAt: z.string().datetime().optional(),
        summarySnippet: z.string().optional(),
      }),
    ),
    total: z.number(),
  }),

  execute: async ({ context }) => {
    // ── Placeholder: DB query not implemented yet ──────────────
    // Future: GET /api/v1/cases/{caseId}/history from FastAPI

    console.warn(
      "[InvestigationHistoryTool] Placeholder — returning empty history.",
    );

    return {
      caseId: "unknown",
      history: [],
      total: 0,
    };
  },
});
