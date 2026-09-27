import type { Metadata } from "next";
import "./globals.css";
import AuthControls from "./components/AuthControls";
import Providers from "./components/SessionProvider";

export const metadata: Metadata = { title: "Pharma AI Assistant", description: "Controlled pharmaceutical knowledge assistant" };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><Providers><AuthControls />{children}</Providers></body></html>;
}
