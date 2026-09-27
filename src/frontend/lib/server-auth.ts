import { getToken } from "next-auth/jwt";
import { headers } from "next/headers";

export async function bearerHeaders(extra?: HeadersInit) {
  const token = await getToken({ req: { headers: headers() } as never, secret: process.env.NEXTAUTH_SECRET });
  if (!token?.accessToken || typeof token.accessToken !== "string") return null;
  return { Authorization: `Bearer ${token.accessToken}`, ...(extra ?? {}) };
}
