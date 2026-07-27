"use client";
import { signIn, signOut, useSession } from "next-auth/react";
export default function AuthControls() {
  const { data: session, status } = useSession();
  if (status === "loading") return null;
  return session ? <button className="auth-control" onClick={() => void signOut({ callbackUrl: "/" })}>Sign out</button> : <button className="auth-control" onClick={() => void signIn("keycloak")}>Sign in</button>;
}
