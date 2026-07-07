/**
 * src/agents/recommendationAgent.ts
 * ────────────────────────────────────
 * RecommendationAgent — generates actionable investigation recommendations.
 *
 * Placeholder step. LLM-based reasoning added in future tasks.
 */

import { createStep } from "@mastra/core/workflows";
import { z } from "zod";
import { logger } from "../logger.js";

export const recommendationAgentStep = createStep({
  id: "recommendation-agent",

  description:
    "Synthesises extracted entities and similar cases to generate " +
    "prioritised, actionable recommendations for the investigator.",

  inputSchema: z.object({
    caseId: z.string(),
    similarCasesFound: z.boolean(),
    similarCases: z.array(
      z.object({
        caseId: z.string(),
        similarityScore: z.number(),
        summary: z.string(),
      }),
    ),
    message: z.string(),
  }),

  outputSchema: z.object({
    caseId: z.string(),
    recommendations: z
      .array(
        z.object({
          priority: z.enum(["high", "medium", "low"]),
          action: z.string(),
          rationale: z.string(),
        }),
      )
      .default([]),
    message: z.string(),
  }),

  execute: async ({ inputData }) => {
    logger.info(
      `[RecommendationAgent] Generating recommendations for ${inputData.caseId}`,
    );

    // ── Placeholder: no reasoning yet ─────────────────────────
    // Future: call Gemini with case context + similar cases

    return {
      caseId: inputData.caseId,
      recommendations: [],
      message:
        "RecommendationAgent placeholder — awaiting LLM integration",
    };
  },
});
