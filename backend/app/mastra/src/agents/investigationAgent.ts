/**
 * src/agents/investigationAgent.ts
 * ─────────────────────────────────
 * InvestigationAgent — entry point of every case workflow.
 *
 * Implemented as a Mastra Step (no LLM required yet).
 * Business logic will be filled in once the LLM integration is ready.
 */

import { createStep } from "@mastra/core/workflows";
import { z } from "zod";
import { logger } from "../logger.js";

export const investigationAgentStep = createStep({
  id: "investigation-agent",

  description:
    "Entry step: validates and initialises the case context before " +
    "handing off to the entity extraction pipeline.",

  inputSchema: z.object({
    caseId: z.string().describe("Unique identifier for the investigation case"),
    rawInput: z
      .string()
      .optional()
      .describe("Raw FIR text or description (populated in future tasks)"),
  }),

  outputSchema: z.object({
    caseId: z.string(),
    status: z.enum(["initialized", "failed"]),
    message: z.string(),
  }),

  execute: async ({ inputData }) => {
    logger.info(
      `[InvestigationAgent] Initialising case ${inputData.caseId}`,
    );

    // ── Placeholder: no business logic yet ────────────────────
    // Future: load case from DB, validate FIR, bootstrap context

    return {
      caseId: inputData.caseId,
      status: "initialized" as const,
      message: "InvestigationAgent placeholder — awaiting LLM integration",
    };
  },
});
