import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "TRACE-X — Forensic Investigation Platform",
  description: "Evidence-centric digital forensics and cyber-triage platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-gray-950 text-gray-100 min-h-screen`}>
        <header className="border-b border-gray-800 bg-gray-900 px-6 py-4 flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded bg-indigo-600 flex items-center justify-center font-bold text-white text-sm">
              TX
            </div>
            <span className="font-semibold text-gray-100 tracking-tight">TRACE-X</span>
            <span className="text-gray-500 text-xs border border-gray-700 rounded px-1.5 py-0.5">MVP</span>
          </div>
        </header>
        <main className="px-6 py-8 max-w-7xl mx-auto">{children}</main>
      </body>
    </html>
  );
}
