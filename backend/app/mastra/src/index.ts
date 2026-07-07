/**
 * src/index.ts
 * ─────────────
 * Mastra instance — root orchestrator for CrimeMind AI.
 *
 * Registers:
 *   - InvestigationWorkflow
 *   - All placeholder tools
 *
 * Note: Agents require a live LLM model and are NOT registered here yet.
 * They will be added once Gemini / OpenAI integration is configured.
 */

import { Mastra } from "@mastra/core";
import { investigationHistoryTool } from "./tools/investigationHistoryTool.js";
import { qdrantSearchTool } from "./tools/qdrantSearchTool.js";
import { reportStorageTool } from "./tools/reportStorageTool.js";
import { investigationWorkflow } from "./workflows/investigationWorkflow.js";
import { logger } from "./logger.js";

export const mastra = new Mastra({
  workflows: {
    investigationWorkflow,
  },
  tools: {
    qdrantSearchTool,
    reportStorageTool,
    investigationHistoryTool,
  },
});

logger.info("[Mastra] Instance initialised successfully.", {
  workflows: ["investigationWorkflow"],
  tools: ["qdrantSearchTool", "reportStorageTool", "investigationHistoryTool"],
});

// Re-export for convenience
export { investigationWorkflow } from "./workflows/investigationWorkflow.js";
export { qdrantSearchTool } from "./tools/qdrantSearchTool.js";
export { reportStorageTool } from "./tools/reportStorageTool.js";
export { investigationHistoryTool } from "./tools/investigationHistoryTool.js";
