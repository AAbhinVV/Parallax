import { NextRequest, NextResponse } from "next/server";

import { createBackendClient, unwrap } from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import { clearTokenCookies, readTokenCookies, setTokenCookies } from "@/lib/auth/cookies";

async function rotateSession() {
  const { refreshToken } = await readTokenCookies();
  if (!refreshToken) throw new ApiError("No refresh session.", 401);
  const tokens = unwrap(await createBackendClient().POST("/api/auth/refresh", { body: { refresh_token: refreshToken } }));
  await setTokenCookies(tokens);
  return tokens;
}

export async function POST(request: Request) {
  const origin = request.headers.get("origin");
  if (origin && origin !== new URL(request.url).origin) return NextResponse.json({ detail: "Invalid origin." }, { status: 403 });
  try {
    const tokens = await rotateSession();
    return NextResponse.json({ expiresAt: Date.now() + tokens.expires_in * 1000 }, { headers: { "Cache-Control": "no-store" } });
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) await clearTokenCookies();
    return NextResponse.json({ detail: error instanceof Error ? error.message : "Refresh failed." }, { status: error instanceof ApiError ? error.status : 500 });
  }
}

export async function GET(request: NextRequest) {
  const requestedNext = request.nextUrl.searchParams.get("next") ?? "/dashboard";
  const safeNext = requestedNext.startsWith("/") && !requestedNext.startsWith("//") ? requestedNext : "/dashboard";
  try {
    await rotateSession();
    return NextResponse.redirect(new URL(safeNext, request.url));
  } catch {
    await clearTokenCookies();
    return NextResponse.redirect(new URL("/login?reason=session-expired", request.url));
  }
}
