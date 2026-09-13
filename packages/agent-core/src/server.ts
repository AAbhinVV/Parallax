import http from "node:http";
import { Command } from "@langchain/langgraph";
import { agentGraph } from "./graph/graph.js";
import {
  analyzeMission,
  type AgentContextRequestBody,
} from "./reasoning/analyze.js";
import type { MissionContext } from "./types/mission-context.js";
import {
  getProgress,
  type MissionResponse,
  type MissionStatus,
} from "./types/mission.js";

const PORT = Number(process.env.AGENT_PORT ?? "4010");

/**
 * Bearer check for the backend contract. Open when no key is configured
 * (local/dev); enforced when AGENT_SERVICE_API_KEY is set.
 */
function isAuthorized(request: http.IncomingMessage): boolean {
  const expected = process.env.AGENT_SERVICE_API_KEY;

  if (!expected) {
    return true;
  }

  return request.headers.authorization === `Bearer ${expected}`;
}

type MissionRequest = {
  mission: string;
  missionId?: string;
  context?: MissionContext | null;
};

const missions = new Map<
  string,
  {
    status: string;
    state: unknown;
  }
>();

function json(
  response: http.ServerResponse,
  statusCode: number,
  body: unknown,
) {
  response.writeHead(statusCode, {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
  });

  response.end(JSON.stringify(body));
}

async function readBody(
  request: http.IncomingMessage,
): Promise<string> {
  return new Promise((resolve, reject) => {
    let body = "";

    request.on("data", (chunk) => {
      body += chunk;
    });

    request.on("end", () => resolve(body));

    request.on("error", reject);
  });
}

function buildMissionInput(
  mission: string,
  context: MissionContext | null,
) {
  return {
    mission,
    context,
    pr: null,
    evidence: [],
    gaps: [],
    risk: null,
    reviewEffort: null,
    reviewerCandidates: [],
    availability: [],
    reviewPlan: null,
    contextPack: null,
    policyRecommendation: null,
    proposedActions: [],
    policyDecision: null,
    executionResults: [],
    verificationResults: [],
    slackSummary: "",
    auditEvents: [],
    approvalStatus: "not_required" as const,
    currentStep: "start",
    errors: [],
  };
}

type MissionStateLike = Record<string, any>;

function deriveStatus(
  state: MissionStateLike,
  interrupted: boolean,
): MissionStatus {
  if (
    state.approvalStatus === "pending" ||
    interrupted
  ) {
    return "waiting_for_approval";
  }

  if (state.errors.length > 0) {
    return "failed";
  }

  return "running";
}

function buildMissionResponse(
  missionId: string,
  state: MissionStateLike,
  status: MissionStatus,
): MissionResponse {
  return {
    missionId,
    status,
    currentStep: state.currentStep,
    progress: getProgress(state.currentStep),
    approvalStatus: state.approvalStatus,
    policyRecommendation:
      state.policyRecommendation ?? null,
    proposedActions: state.proposedActions ?? [],
    executionResults: state.executionResults ?? [],
    verificationResults:
      state.verificationResults ?? [],
    slackSummary: state.slackSummary ?? "",
    errors: state.errors ?? [],
  };
}

const server = http.createServer(
  async (request, response) => {
    try {
      if (request.method === "OPTIONS") {
        response.writeHead(204, {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Headers":
            "Content-Type",
          "Access-Control-Allow-Methods":
            "GET,POST,OPTIONS",
        });
        response.end();
        return;
      }

      const url = new URL(
        request.url ?? "/",
        `http://${request.headers.host ?? "localhost"}`,
      );

      if (
        request.method === "GET" &&
        url.pathname === "/health"
      ) {
        json(response, 200, {
          status: "ok",
          service: "agent-core",
        });

        return;
      }

      if (
        request.method === "POST" &&
        url.pathname === "/v1/analyze"
      ) {
        if (!isAuthorized(request)) {
          json(response, 401, {
            error: "Unauthorized",
          });

          return;
        }

        const rawBody = await readBody(request);

        let body: AgentContextRequestBody;
        try {
          body = JSON.parse(rawBody) as AgentContextRequestBody;
        } catch {
          json(response, 400, {
            error: "Invalid JSON body",
          });

          return;
        }

        if (
          typeof body.prompt !== "string" ||
          body.prompt.length === 0 ||
          !Array.isArray(body.evidence)
        ) {
          json(response, 400, {
            error: "prompt and evidence are required",
          });

          return;
        }

        try {
          const result = await analyzeMission(body);

          json(response, 200, result);
        } catch (error) {
          console.error(error);

          json(response, 422, {
            error:
              error instanceof Error
                ? error.message
                : String(error),
          });
        }

        return;
      }

      if (
        request.method === "POST" &&
        url.pathname === "/missions"
      ) {
        const rawBody = await readBody(request);

        const body = JSON.parse(rawBody) as MissionRequest;

        if (
          !body.mission ||
          typeof body.mission !== "string"
        ) {
          json(response, 400, {
            error: "mission is required",
          });
          return;
        }

        const missionId =
          body.missionId ??
          `mission-${Date.now()}`;

        const state = await agentGraph.invoke(
          buildMissionInput(body.mission, body.context ?? null),
          {
            configurable: {
              thread_id: missionId,
            },
          },
        );

        const interrupted = Boolean(
          "__interrupt__" in state,
        );

        const status = deriveStatus(
          state,
          interrupted,
        );

        missions.set(missionId, {
          status,
          state,
        });

        json(
          response,
          202,
          buildMissionResponse(
            missionId,
            state,
            status,
          ),
        );

        return;
      }

      const missionMatch =
        url.pathname.match(
          /^\/missions\/([^/]+)$/,
        );

      if (
        request.method === "GET" &&
        missionMatch
      ) {
        const missionId = missionMatch[1];

        const mission = missions.get(missionId);

        if (!mission) {
          json(response, 404, {
            error: "Mission not found",
          });
          return;
        }

        json(
          response,
          200,
          buildMissionResponse(
            missionId,
            mission.state as MissionStateLike,
            mission.status as MissionStatus,
          ),
        );

        return;
      }

      const approvalMatch =
        url.pathname.match(
          /^\/missions\/([^/]+)\/(approve|reject)$/,
        );

      if (
        request.method === "POST" &&
        approvalMatch
      ) {
        const missionId = approvalMatch[1];
        const decision = approvalMatch[2];

        const existing =
          missions.get(missionId);

        if (!existing) {
          json(response, 404, {
            error: "Mission not found",
          });
          return;
        }

        const state =
          await agentGraph.invoke(
            new Command({
              resume:
                decision === "approve"
                  ? "approved"
                  : "rejected",
            }),
            {
              configurable: {
                thread_id: missionId,
              },
            },
          );

        const status: MissionStatus =
          decision === "reject"
            ? "rejected"
            : state.errors.length > 0
              ? "failed"
              : (
                  state.executionResults as Array<{
                    success?: boolean;
                  }>
                ).some((result) => !result.success)
                ? "partially_complete"
                : "completed";

        missions.set(missionId, {
          status,
          state,
        });

        json(
          response,
          200,
          buildMissionResponse(
            missionId,
            state,
            status,
          ),
        );

        return;
      }

      json(response, 404, {
        error: "Route not found",
      });
    } catch (error) {
      console.error(error);

      json(response, 500, {
        error:
          error instanceof Error
            ? error.message
            : String(error),
      });
    }
  },
);

server.listen(PORT, () => {
  console.log(
    `Parallax Agent Core listening on http://localhost:${PORT}`,
  );
});