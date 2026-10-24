/**
 * CD-AVC extension for the pi coding agent.
 *
 * Two jobs:
 * 1. PROTECT the fixed evaluator: the improving agent can edit the harness
 *    config surface, but never the evaluation authority (protected task list,
 *    dev2/held-out tests, hidden tests anywhere, the improvement log).
 * 2. EXPOSE deterministic verification: a `cdavc_verify` tool that runs the
 *    public gates for a dev2 task and returns structured feedback, and a
 *    `/cdavc-improve` command that runs the self-improvement loop in
 *    SIMULATED mode (live, token-spending runs stay human-gated on the CLI).
 *
 * Load: pi --extension pi_extension/cdavc/index.ts
 * or copy the cdavc/ directory into ~/.pi/agent/extensions/
 */

import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { Type } from "@earendil-works/pi-ai";
import { defineTool, type ExtensionAPI } from "@earendil-works/pi-coding-agent";

const execFileAsync = promisify(execFile);

// Paths the improving agent must never write. The evaluation authority is
// fixed; a change here is a human decision, not a self-improvement step.
const PROTECTED = [
  "benchmarks_heldout/",
  "self_improve/protected/",
  "self_improve/IMPROVE_LOG.md",
  "hidden_tests.py",
];

function isProtected(path: string): boolean {
  const norm = path.replace(/\\/g, "/");
  return PROTECTED.some((p) => norm.includes(p));
}

const verifyTool = defineTool({
  name: "cdavc_verify",
  label: "CD-AVC Verify",
  description:
    "Run the deterministic public gates for a dev2 benchmark task against a " +
    "candidate solution. Returns pass/fail plus the public test output. " +
    "Hidden tests are the fixed evaluation authority and are never run here.",
  parameters: Type.Object({
    task_dir: Type.String({
      description: "Task directory relative to the repo root, e.g. benchmarks_dev2/agent10/task_e03_wrap_text",
    }),
    solution: Type.String({
      description: "Solution filename inside the task directory, e.g. solution_stub.py",
    }),
  }),

  async execute(_toolCallId, params, _signal, _onUpdate, _ctx) {
    if (isProtected(params.task_dir) || isProtected(params.solution)) {
      return {
        content: [{ type: "text", text: "Refused: path is inside the protected evaluator surface." }],
        details: { ok: false, refused: true },
      };
    }
    if (!params.task_dir.startsWith("benchmarks_dev2/")) {
      return {
        content: [{ type: "text", text: "Refused: cdavc_verify only covers benchmarks_dev2 tasks." }],
        details: { ok: false, refused: true },
      };
    }
    try {
      const { stdout, stderr } = await execFileAsync(
        "python3",
        [`${params.task_dir}/public_tests.py`, params.solution],
        { timeout: 60_000 },
      );
      return {
        content: [{ type: "text", text: `PUBLIC GATES: PASS\n${stdout}`.trim() }],
        details: { ok: true },
      };
    } catch (err: any) {
      const output = `${err.stdout ?? ""}\n${err.stderr ?? err.message}`.trim().slice(-4000);
      return {
        content: [{ type: "text", text: `PUBLIC GATES: FAIL\n${output}` }],
        details: { ok: false, output },
      };
    }
  },
});

export default function (pi: ExtensionAPI) {
  pi.registerTool(verifyTool);

  // Block writes/edits to the fixed evaluation authority.
  pi.on("tool_call", async (event, ctx) => {
    if (event.toolName !== "write" && event.toolName !== "edit") {
      return undefined;
    }
    const path = String((event.input as { path?: unknown }).path ?? "");
    if (isProtected(path)) {
      if (ctx.hasUI) {
        ctx.ui.notify(`Blocked write to protected evaluator path: ${path}`, "warning");
      }
      return {
        block: true,
        reason:
          `"${path}" is part of the fixed CD-AVC evaluation authority. ` +
          "The improving agent may edit self_improve/harness_config.json only.",
      };
    }
    return undefined;
  });

  // Self-improvement loop, simulated mode only. Live measured runs spend
  // tokens and stay human-gated: run `python -m self_improve.run
  // --evaluator live --approve-spend --token-cap N` from the CLI instead.
  pi.registerCommand("cdavc-improve", {
    description: "Run the CD-AVC self-improvement loop (simulated, offline)",
    handler: async (args, ctx) => {
      const iterations = args.trim() || "3";
      try {
        const { stdout } = await execFileAsync(
          "python3",
          ["-m", "self_improve.run", "--iterations", iterations, "--evaluator", "simulated"],
          { timeout: 120_000 },
        );
        ctx.ui.notify(stdout.trim() || "self-improve loop finished", "info");
      } catch (err: any) {
        ctx.ui.notify(`self-improve loop failed: ${err.message}`, "error");
      }
    },
  });
}
