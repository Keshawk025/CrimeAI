import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "CrimeMind AI – Investigation Copilot for Law Enforcement",
  description:
    "AI-powered investigation copilot built for Law Enforcement. Accelerate case resolution with intelligent document analysis, timeline reconstruction, and evidence correlation.",
  keywords: [
    "CrimeMind AI",
    "Law Enforcement",
    "AI Investigation",
    "Crime Analysis",
    "Hackathon",
  ],
  authors: [{ name: "CrimeMind AI Team" }],
  openGraph: {
    title: "CrimeMind AI – Investigation Copilot",
    description:
      "AI-powered investigation copilot built for Law Enforcement.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
