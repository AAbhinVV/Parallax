import { NextRequest, NextResponse } from "next/server";

import { sessionCookies } from "@/lib/auth/constants";

export function proxy(request: NextRequest) {
  if (process.env.PARALLAX_DISABLE_AUTH === "true") return NextResponse.next();
  const accessToken = request.cookies.get(sessionCookies.access)?.value;
  const refreshToken = request.cookies.get(sessionCookies.refresh)?.value;
  const expiresAt = Number(request.cookies.get(sessionCookies.expires)?.value || 0);
  const needsRefresh = !accessToken || !expiresAt || expiresAt <= Date.now() + 5_000;

  if (!needsRefresh) return NextResponse.next();
  if (!refreshToken) return NextResponse.redirect(new URL("/login", request.url));

  const refreshUrl = new URL("/api/session/refresh", request.url);
  refreshUrl.searchParams.set("next", `${request.nextUrl.pathname}${request.nextUrl.search}`);
  return NextResponse.redirect(refreshUrl);
}

export const config = {
  matcher: [
    "/dashboard/:path*",
    "/missions/:path*",
    "/projects/:path*",
    "/integrations/:path*",
    "/activity/:path*",
    "/team/:path*",
    "/analytics/:path*",
    "/settings/:path*",
  ],
};
