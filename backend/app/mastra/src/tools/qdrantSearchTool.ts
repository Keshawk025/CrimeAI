/**
 * src/tools/qdrantSearchTool.ts
 * ──────────────────────────────
 * QdrantSearchTool — semantic similarity search over the crime_reports collection.
 *
 * Placeholder. Qdrant client wiring happens in the next dedicated task.
 */

import { createTool } from "@mastra/core/tools";
import { z } from "zod";

export const qdrantSearchTool = createTool({
  id: "qdrant-search",

  description:
    "Performs a cosine-similarity nearest-neighbour search in the Qdrant " +
    "crime_reports collection and returns the top-k most similar documents.",

  inputSchema: z.object({
    queryVector: z
      .array(z.number())
      .describe("Dense embedding vector (dim=768) for the query"),
    topK: z
      .number()
      .int()
      .min(1)
      .max(50)
      .default(5)
      .describe("Maximum number of results to return"),
    collectionName: z
      .string()
      .default("crime_reports")
      .describe("Qdrant collection to search"),
  }),

  outputSchema: z.object({
    results: z.array(
      z.object({
        id: z.string(),
        score: z.number(),
        payload: z.record(z.unknown()),
      }),
    ),
    total: z.number(),
  }),

  execute: async ({ context }) => {
    // ── Placeholder: Qdrant client not wired yet ───────────────
    // Future: call QdrantService.search_similar() via HTTP or direct client

    console.warn(
      "[QdrantSearchTool] Placeholder — returning empty results. Wire Qdrant in Task 4.",
    );

    return {
      results: [],
      total: 0,
    };
  },
});
