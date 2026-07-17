import { NextRequest, NextResponse } from "next/server";
import { getAuthBffConfig } from "../../../../lib/auth/config";
import { authErrorResponse } from "../../../../lib/auth/errors";
import { assertValidMutationOrigin } from "../../../../lib/auth/origin";
import { clearSessionCookie } from "../../../../lib/auth/session";

export async function POST(request: NextRequest) {
  try {
    const config = getAuthBffConfig();
    assertValidMutationOrigin(request, config);

    const response = NextResponse.json({ success: true });
    clearSessionCookie(response, config);
    return response;
  } catch (error) {
    return authErrorResponse(error);
  }
}
