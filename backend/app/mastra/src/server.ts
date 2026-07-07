/**
 * src/server.ts
 * ──────────────
 * Lightweight Hono HTTP server exposing the Mastra workflow API.
 *
 * Endpoints:
 *   GET  /health             — liveness probe
 *   POST /api/workflow/test  — trigger InvestigationWorkflow with a test case
 *
 * Default port: 4111  (configurable via MASTRA_PORT env var)
 */

import { serve } from "@hono/node-server";
import { Hono } from "hono";
import { mastra, investigationWorkflow } from "./index.js";
import { logger } from "./logger.js";

const PORT = parseInt(process.env["MASTRA_PORT"] ?? "4111", 10);

const app = new Hono();

// ── Middleware: structured request logging ─────────────────────────────────────

app.use("*", async (c, next) => {
  const start = Date.now();
  await next();
  const ms = Date.now() - start;
  logger.info(`${c.req.method} ${c.req.path} → ${c.res.status} (${ms}ms)`);
});

// ── Health ─────────────────────────────────────────────────────────────────────

app.get("/health", (c) => {
  return c.json({ status: "ok", service: "crimemind-mastra" });
});

// ── POST /api/workflow/test ────────────────────────────────────────────────────

app.post("/api/workflow/test", async (c) => {
  logger.info("[WorkflowTest] Received request to execute InvestigationWorkflow.");

  try {
    // Create a workflow run with a synthetic test case
    const testCaseId = `test-${Date.now()}`;
    logger.info(`[WorkflowTest] Starting workflow run for case: ${testCaseId}`);

    const run = await investigationWorkflow.createRun();

    logger.info(`[WorkflowTest] Run created: ${run.runId}`);

    // Execute all 5 pipeline steps synchronously for the test endpoint
    const result = await run.start({ inputData: { caseId: testCaseId } });

    logger.info(`[WorkflowTest] Workflow completed for run: ${run.runId}`, {
      runId: run.runId,
      caseId: testCaseId,
      status: result?.status,
    });

    return c.json(
      {
        status: "Workflow initialized successfully",
        runId: run.runId,
        caseId: testCaseId,
        workflowId: investigationWorkflow.id,
        steps: [
          "investigation-agent",
          "entity-extraction-agent",
          "similar-case-agent",
          "recommendation-agent",
          "report-generation-agent",
        ],
      },
      200,
    );
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    logger.error("[WorkflowTest] Workflow execution failed.", { error: message });

    return c.json(
      {
        status: "error",
        message,
      },
      500,
    );
  }
});

// ── Boot ───────────────────────────────────────────────────────────────────────

logger.info(`[Mastra Server] Starting on port ${PORT}…`);

serve(
  {
    fetch: app.fetch,
    port: PORT,
  },
  () => {
    logger.info(`[Mastra Server] Listening on http://0.0.0.0:${PORT}`);
    logger.info(`[Mastra Server] Test endpoint: POST http://0.0.0.0:${PORT}/api/workflow/test`);
  },
);
