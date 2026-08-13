import type { Metadata } from "next";
import { DM_Serif_Display, Newsreader } from "next/font/google";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import "./globals.css";

const serif = Newsreader({ subsets: ["latin"], style: ["normal", "italic"], variable: "--font-serif" });
const heroSerif = DM_Serif_Display({ subsets: ["latin"], weight: "400", variable: "--font-hero-serif" });

export const metadata: Metadata = {
  metadataBase: new URL("https://fintrace-fawn.vercel.app"),
  title: "FinTrace - Claims checked against filed numbers",
  description: "An evidence-first financial review pipeline.",
  openGraph: {
    title: "FinTrace - Evidence before interpretation",
    description: "Financial claims checked against filed values with scoped model calls, deterministic calculation, quote validation, and human review.",
    type: "website",
    url: "https://fintrace-fawn.vercel.app",
    siteName: "FinTrace",
  },
  twitter: {
    card: "summary_large_image",
    title: "FinTrace - Evidence before interpretation",
    description: "What they said. What they filed. What the math says.",
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <head>
        <meta charSet="UTF-8" />
      </head>
      <body className={`${GeistSans.variable} ${GeistMono.variable} ${serif.variable} ${heroSerif.variable}`}>{children}</body>
    </html>
  );
}
