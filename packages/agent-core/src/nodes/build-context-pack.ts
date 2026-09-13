import type { AgentStateType } from "../graph/state.js";
import { ContextPackSchema } from "../schemas/index.js";

export async function buildContextPack(
  state: AgentStateType,
): Promise<Partial<AgentStateType>> {
  if (!state.pr || !state.risk) {
    return {
      currentStep: "build_context_pack",
      errors: [
        "Cannot build context pack without PR and risk assessment.",
      ],
    };
  }

  if (!state.reviewPlan) {
    return {
      currentStep: "build_context_pack",
      errors: [
        "Cannot build context pack without a review plan.",
      ],
    };
  }

  const changedFilesEvidence = state.evidence.find(
    (item) => item.type === "changed_files",
  );

  const files = changedFilesEvidence
    ? changedFilesEvidence.content
        .split("\n")
        .map((file) => file.trim())
        .filter(Boolean)
    : [];

  const contextPack = ContextPackSchema.parse({
    pr: state.pr,

    whyThisPRExists: {
      acceptanceCriteria: [],
      productContext:
        "Product context was not provided in the available evidence.",
    },

    whatChanged: {
      files:
        files.length > 0
          ? files
          : ["Changed files were not available in the collected evidence."],

      functionalSummary: state.pr.description,

      architecturalImpact:
        "Architectural impact could not be determined from the available evidence.",

      dependencies: [],
    },

    risk: state.risk,

    evidence: state.evidence,

    reviewPlan: state.reviewPlan,
  });

  return {
    currentStep: "build_context_pack",
    contextPack,
  };
}