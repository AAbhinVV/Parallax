import type { AgentStateType } from "../graph/state.js";
import { MockAvailabilityTool } from "../tools/mock-availability.js";

const availabilityTool = new MockAvailabilityTool();

export async function checkAvailability(
  state: AgentStateType,
): Promise<Partial<AgentStateType>> {
  if (state.reviewerCandidates.length === 0) {
    return {
      currentStep: "check_availability",
      errors: ["Cannot check availability without reviewer candidates."],
    };
  }

  const reviewerIds = state.reviewerCandidates.map(
    (candidate) => candidate.id,
  );

  const availability =
    await availabilityTool.getAvailability(reviewerIds);

  return {
    currentStep: "check_availability",
    availability,
  };
}