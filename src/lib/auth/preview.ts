import "server-only";

import type { MeResponse } from "@/lib/api/types";

export const authDisabled = process.env.PARALLAX_DISABLE_AUTH === "true";

const previewWorkspace = {
  id: "00000000-0000-4000-8000-000000000001",
  name: "Parallax Preview",
  slug: "parallax-preview",
  role: "owner" as const,
};

/** Local-only shell identity used when authentication is explicitly disabled. */
export const previewSession: MeResponse & { expiresAt: number } = {
  user: {
    id: "00000000-0000-4000-8000-000000000002",
    email: "preview@parallax.local",
    display_name: "Local Developer",
    is_active: true,
    created_at: "1970-01-01T00:00:00Z",
  },
  current_workspace: previewWorkspace,
  workspaces: [previewWorkspace],
  expiresAt: 0,
};
