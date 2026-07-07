/**
 * src/agents/similarCaseAgent.ts
 * ────────────────────────────────
 * SimilarCaseAgent — retrieves semantically similar historical cases.
 *
 * Placeholder step. Qdrant vector search integrated in future tasks.
 */

import { createStep } from "@mastra/core/workflows";
import { z } from "zod";
import { logger } from "../logger.js";

export const similarCaseAgentStep = createStep({
  id: "similar-case-agent",

  description:
    "Queries the Qdrant vector store to find historically similar cases " +
    "based on entity embeddings and semantic similarity.",

  inputSchema: z.object({
    caseId: z.string(),
    entitiesExtracted: z.boolean(),
    entities: z.array(
      z.object({
        type: z.string(),
        value: z.string(),
      }),
    ),
    message: z.string(),
  }),

  outputSchema: z.object({
    caseId: z.string(),
    similarCasesFound: z.boolean(),
    similarCases: z
      .array(
        z.object({
          caseId: z.string(),
          similarityScore: z.number(),
          summary: z.string(),
        }),
      )
      .default([]),
    message: z.string(),
  }),

  execute: async ({ inputData }) => {
    logger.info(
      `[SimilarCaseAgent] Searching similar cases for ${inputData.caseId}`,
    );

    // ── Placeholder: Qdrant search not wired yet ──────────────
    // Future: call QdrantSearchTool with entity embeddings

    return {
      caseId: inputData.caseId,
      similarCasesFound: false,
      similarCases: [],
      message: "SimilarCaseAgent placeholder — awaiting Qdrant integration",
    };
  },
});
