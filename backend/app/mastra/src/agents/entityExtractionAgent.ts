/**
 * src/agents/entityExtractionAgent.ts
 * ─────────────────────────────────────
 * EntityExtractionAgent — extracts named entities from case documents.
 *
 * Placeholder step. Logic (NER, LLM entity extraction) added in future tasks.
 */

import { createStep } from "@mastra/core/workflows";
import { z } from "zod";
import { logger } from "../logger.js";

export const entityExtractionAgentStep = createStep({
  id: "entity-extraction-agent",

  description:
    "Extracts named entities (persons, locations, dates, organisations) " +
    "from FIR text and case documents using LLM-powered NER.",

  inputSchema: z.object({
    caseId: z.string(),
    status: z.enum(["initialized", "failed"]),
    message: z.string(),
  }),

  outputSchema: z.object({
    caseId: z.string(),
    entitiesExtracted: z.boolean(),
    entities: z
      .array(
        z.object({
          type: z.string(),
          value: z.string(),
        }),
      )
      .default([]),
    message: z.string(),
  }),

  execute: async ({ inputData }) => {
    logger.info(
      `[EntityExtractionAgent] Processing case ${inputData.caseId}`,
    );

    // ── Placeholder: no entity extraction yet ─────────────────
    // Future: call Gemini / LLM for NER on case documents

    return {
      caseId: inputData.caseId,
      entitiesExtracted: false,
      entities: [],
      message: "EntityExtractionAgent placeholder — awaiting LLM integration",
    };
  },
});
