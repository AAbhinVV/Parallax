import type { AvailabilitySlot } from "../schemas/index.js";

export interface AvailabilityTool {
  getAvailability(reviewerIds: string[]): Promise<AvailabilitySlot[]>;
}

export class MockAvailabilityTool implements AvailabilityTool {
  async getAvailability(
    reviewerIds: string[],
  ): Promise<AvailabilitySlot[]> {
    const slots: AvailabilitySlot[] = [
      {
        reviewerId: "reviewer-1",
        start: "2026-09-13T10:00:00+05:30",
        end: "2026-09-13T12:00:00+05:30",
        durationMinutes: 120,
      },
      {
        reviewerId: "reviewer-2",
        start: "2026-09-13T11:00:00+05:30",
        end: "2026-09-13T14:00:00+05:30",
        durationMinutes: 180,
      },
      {
        reviewerId: "reviewer-3",
        start: "2026-09-13T15:00:00+05:30",
        end: "2026-09-13T16:00:00+05:30",
        durationMinutes: 60,
      },
    ];

    return slots.filter((slot) =>
      reviewerIds.includes(slot.reviewerId),
    );
  }
}