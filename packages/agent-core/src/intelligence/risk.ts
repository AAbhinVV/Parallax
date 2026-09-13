import type {
  PR,
  Evidence,
  RiskSignal,
  RiskAssessment,
} from "../schemas/index.js";

const CATEGORY_WEIGHTS: Record<string, number> = {
  security: 20,
  payments: 25,
  data: 20,
  api: 15,
  concurrency: 15,
  configuration: 10,
  infrastructure: 15,
  rollback: 15,
  change_size: 10,
  ownership: 10,
  freshness: 5,
  related_failures: 20,
};

function createSignal(
  category: RiskSignal["category"],
  description: string,
  evidence: Evidence[],
): RiskSignal {
  return {
    category,
    description,
    score: CATEGORY_WEIGHTS[category],
    evidence,
  };
}

export function calculateRisk(
  pr: PR,
  evidence: Evidence[],
): RiskAssessment {
  const signals: RiskSignal[] = [];

  const allText = [
    pr.title,
    pr.description,
    ...evidence.map((item) => item.content),
  ]
    .join(" ")
    .toLowerCase();

  /* ---------------------------------------------------------------------- */
  /* Payments                                                               */
  /* ---------------------------------------------------------------------- */

  if (
    allText.includes("payment") ||
    allText.includes("transaction") ||
    allText.includes("billing")
  ) {
    signals.push(
      createSignal(
        "payments",
        "The change affects payment or transaction processing.",
        evidence.filter(
          (item) =>
            item.content.toLowerCase().includes("payment") ||
            item.content.toLowerCase().includes("transaction"),
        ),
      ),
    );
  }

  /* ---------------------------------------------------------------------- */
  /* Data                                                                   */
  /* ---------------------------------------------------------------------- */

  if (
    allText.includes("database") ||
    allText.includes("transaction") ||
    allText.includes("migration")
  ) {
    signals.push(
      createSignal(
        "data",
        "The change affects database or transactional data handling.",
        evidence.filter(
          (item) =>
            item.content.toLowerCase().includes("database") ||
            item.content.toLowerCase().includes("transaction") ||
            item.content.toLowerCase().includes("migration"),
        ),
      ),
    );
  }

  /* ---------------------------------------------------------------------- */
  /* Rollback                                                               */
  /* ---------------------------------------------------------------------- */

  if (
    allText.includes("rollback") ||
    allText.includes("retry") ||
    allText.includes("failure")
  ) {
    signals.push(
      createSignal(
        "rollback",
        "The change modifies failure handling or rollback behavior.",
        evidence.filter(
          (item) =>
            item.content.toLowerCase().includes("rollback") ||
            item.content.toLowerCase().includes("retry") ||
            item.content.toLowerCase().includes("failure"),
        ),
      ),
    );
  }

  /* ---------------------------------------------------------------------- */
  /* API                                                                    */
  /* ---------------------------------------------------------------------- */

  if (
    allText.includes("api") ||
    allText.includes("endpoint") ||
    allText.includes("request")
  ) {
    signals.push(
      createSignal(
        "api",
        "The change may affect API request or response behavior.",
        evidence.filter(
          (item) =>
            item.content.toLowerCase().includes("api") ||
            item.content.toLowerCase().includes("endpoint") ||
            item.content.toLowerCase().includes("request"),
        ),
      ),
    );
  }

  /* ---------------------------------------------------------------------- */
  /* Concurrency                                                            */
  /* ---------------------------------------------------------------------- */

  if (
    allText.includes("concurrency") ||
    allText.includes("race") ||
    allText.includes("parallel") ||
    allText.includes("lock")
  ) {
    signals.push(
      createSignal(
        "concurrency",
        "The change may introduce concurrency or race-condition concerns.",
        evidence,
      ),
    );
  }

  /* ---------------------------------------------------------------------- */
  /* Security                                                               */
  /* ---------------------------------------------------------------------- */

  if (
    allText.includes("auth") ||
    allText.includes("permission") ||
    allText.includes("token") ||
    allText.includes("credential") ||
    allText.includes("security")
  ) {
    signals.push(
      createSignal(
        "security",
        "The change may affect authentication, authorization, or credentials.",
        evidence,
      ),
    );
  }

  /* ---------------------------------------------------------------------- */
  /* Change size                                                            */
  /* ---------------------------------------------------------------------- */

  if (pr.filesChanged >= 10 || pr.additions + pr.deletions >= 500) {
    signals.push(
      createSignal(
        "change_size",
        "The pull request contains a relatively large change set.",
        evidence,
      ),
    );
  }

  /* ---------------------------------------------------------------------- */
  /* Calculate overall score                                                */
  /* ---------------------------------------------------------------------- */

  const rawScore = signals.reduce(
    (total, signal) => total + signal.score,
    0,
  );

  const score = Math.min(rawScore, 100);

  let level: RiskAssessment["level"];

  if (score >= 80) {
    level = "critical";
  } else if (score >= 60) {
    level = "high";
  } else if (score >= 30) {
    level = "medium";
  } else {
    level = "low";
  }

  return {
    level,
    score,
    signals,
    explanation:
      signals.length === 0
        ? "No significant risk signals were detected."
        : `Detected ${signals.length} significant engineering risk signal(s).`,
    confidence: signals.length > 0 ? 0.85 : 0.7,
  };
}