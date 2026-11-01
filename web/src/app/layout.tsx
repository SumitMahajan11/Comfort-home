import type { Metadata } from "next";
import { Source_Serif_4, IBM_Plex_Sans, IBM_Plex_Sans_Devanagari, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { PersistentDisclaimer } from "@/components/common/PersistentDisclaimer";

const sourceSerif = Source_Serif_4({
  subsets: ["latin"],
  weight: ["600"],
  variable: "--font-serif",
  display: "swap",
});

const ibmPlexSans = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-sans",
  display: "swap",
});

const ibmPlexSansDevanagari = IBM_Plex_Sans_Devanagari({
  subsets: ["devanagari"],
  weight: ["400", "500", "600"],
  variable: "--font-devanagari",
  display: "swap",
});

const ibmPlexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-code",
  display: "swap",
});

export const metadata: Metadata = {
  title: "ClimateAdapt-Comfort | Passive Shelter Decision-Support Across Indian Climate Zones",
  description: "Decision-support system integrating ASHRAE DB II field comfort surveys, EnergyPlus building simulation, XGBoost surrogates, and NSGA-II Pareto optimization for passive shelter design across Indian climate zones.",
  keywords: ["Thermal Comfort", "Passive Shelter", "EnergyPlus", "ASHRAE DB II", "Indian Climates", "NSGA-II", "Surrogate Modeling", "SHAP"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`light ${sourceSerif.variable} ${ibmPlexSans.variable} ${ibmPlexSansDevanagari.variable} ${ibmPlexMono.variable}`}
      data-theme="light"
      suppressHydrationWarning
    >
      <head>
        <script
          id="theme-init"
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem('theme');if(t==='dark'||(!t&&window.matchMedia&&window.matchMedia('(prefers-color-scheme: dark)').matches)){document.documentElement.classList.add('dark');document.documentElement.classList.remove('light');document.documentElement.setAttribute('data-theme','dark');}else{document.documentElement.classList.remove('dark');document.documentElement.classList.add('light');document.documentElement.setAttribute('data-theme','light');}}catch(e){}})();`,
          }}
        />
      </head>
      <body suppressHydrationWarning className="min-h-screen flex flex-col antialiased selection:bg-[var(--primary)] selection:text-[var(--primary-contrast)] relative bg-[var(--bg)] text-[var(--ink)] transition-colors duration-200">
        <PersistentDisclaimer />
        <Navbar />
        <main className="flex-1 max-w-[1280px] w-full mx-auto px-4 sm:px-6 pt-6 pb-12 relative z-10">
          {children}
        </main>
        <Footer />
      </body>
    </html>
  );
}
