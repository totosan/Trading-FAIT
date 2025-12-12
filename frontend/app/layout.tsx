import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Trading-FAIT",
  description: "AI-Agenten Trading-Webapp mit Magentic-One + Azure OpenAI",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="de">
      <body className="min-h-screen bg-background antialiased">
        {children}
      </body>
    </html>
  );
}
