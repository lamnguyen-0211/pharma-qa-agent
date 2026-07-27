import type { NextAuthOptions } from "next-auth";
import KeycloakProvider from "next-auth/providers/keycloak";

export const authOptions: NextAuthOptions = {
  providers: [KeycloakProvider({
    clientId: process.env.KEYCLOAK_CLIENT_ID ?? "pharma-frontend",
    clientSecret: process.env.KEYCLOAK_CLIENT_SECRET ?? "local-development-secret",
    issuer: process.env.KEYCLOAK_ISSUER ?? "http://127.0.0.1:8081/realms/pharma-manager",
  })],
  session: { strategy: "jwt" },
  callbacks: {
    async jwt({ token, account }) {
      if (account?.access_token) token.accessToken = account.access_token;
      return token;
    },
    async session({ session, token }) {
      return session;
    },
  },
  secret: process.env.NEXTAUTH_SECRET,
};
