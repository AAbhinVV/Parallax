import type { AgentStateType } from "../graph/state.js";
import type { GapMismatch } from "../schemas/index.js";

export async function detectGaps(
  state: AgentStateType,
): Promise<Partial<AgentStateType>> {
  const gaps: GapMismatch[] = [];

  if (!state.pr) {
    return {
      currentStep: "detect_gaps",
      errors: ["Cannot detect gaps without a pull request."],
    };
  }

  const githubFilesEvidence = state.evidence.find(
    (item) =>
      item.source === "github" && item.type === "changed_files",
  );

  if (githubFilesEvidence) {
    const reportedFiles = state.pr.filesChanged;
    const observedFiles = githubFilesEvidence.content
      .split("\n")
      .filter(Boolean).length;

    if (observedFiles !== reportedFiles) {
      gaps.push({
        type: "mismatch",
        description: `PR metadata reports ${reportedFiles} changed files, but the collected GitHub evidence contains ${observedFiles} file paths.`,
        sources: ["github"],
        severity: "medium",
      });
    }
  } else {
    gaps.push({
      type: "gap",
      description: "Changed-file evidence was not available from GitHub.",
      sources: ["github"],
      severity: "high",
    });
  }

  const jiraEvidence = state.evidence.find(
    (item) => item.source === "jira" && item.type === "issue",
  );

  if (!jiraEvidence) {
    gaps.push({
      type: "gap",
      description: "No linked Jira issue was found in the collected context.",
      sources: ["jira"],
      severity: "medium",
    });
  }

  const notionEvidence = state.evidence.find(
    (item) =>
      item.source === "notion" && item.type === "project_context",
  );

  if (!notionEvidence) {
    gaps.push({
      type: "gap",
      description: "No Notion project context was found in the collected context.",
      sources: ["notion"],
      severity: "low",
    });
  }

  return {
    currentStep: "detect_gaps",
    gaps,
  };
}