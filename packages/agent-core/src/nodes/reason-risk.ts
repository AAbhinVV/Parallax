import {
  HumanMessage,
  SystemMessage,
} from "@langchain/core/messages";

import type { AgentStateType } from "../graph/state.js";
import { getModelGateway } from "../reasoning/reason.js";

export async function reasonAboutRisk(
  state: AgentStateType,
): Promise<Partial<AgentStateType>> {
  if (!state.pr || !state.risk) {
    return {
      currentStep: "reason_risk",
      errors: [
        "Risk reasoning requires both PR information and deterministic risk assessment.",
      ],
    };
  }

  const prompt = `
You are a senior software engineer reviewing a pull request.

Analyze the pull request using ONLY the supplied evidence and deterministic risk signals.

Do not invent facts.

PR:
Title: ${state.pr.title}
Description: ${state.pr.description}
Repository: ${state.pr.repository}
Files changed: ${state.pr.filesChanged}
Additions: ${state.pr.additions}
Deletions: ${state.pr.deletions}

Evidence:
${JSON.stringify(state.evidence, null, 2)}

Deterministic risk assessment:
${JSON.stringify(state.risk, null, 2)}

Provide a concise engineering assessment covering:

1. Why the detected risks matter.
2. What a reviewer should specifically inspect.
3. Whether the current risk classification appears reasonable.
4. Any important uncertainty caused by missing evidence.

Do not invent repository history, incidents, ownership, metrics, or behavior that is not present in the supplied information.
`;

  const response = await getModelGateway().invoke([
    new SystemMessage(
      "You are a careful senior software engineer. Base conclusions only on supplied evidence.",
    ),
    new HumanMessage(prompt),
  ]);

  return {
    currentStep: "reason_risk",
    risk: {
      ...state.risk,
      explanation: `${state.risk.explanation}\n\nAI reasoning:\n${response}`,
    },
  };
}