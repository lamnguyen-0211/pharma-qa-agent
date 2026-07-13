import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = { title: "Pharma AI Assistant", description: "Controlled pharmaceutical knowledge assistant" };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
