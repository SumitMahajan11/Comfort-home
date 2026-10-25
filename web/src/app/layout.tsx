import type { Metadata } from "next";
import "./globals.css";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { PersistentDisclaimer } from "@/components/common/PersistentDisclaimer";

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
    <html lang="en" className="dark" data-theme="dark" suppressHydrationWarning>
      <head>
        <script
          id="theme-init"
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem('theme');if(t==='light'){document.documentElement.classList.remove('dark');document.documentElement.classList.add('light');document.documentElement.setAttribute('data-theme','light');}else{document.documentElement.classList.add('dark');document.documentElement.classList.remove('light');document.documentElement.setAttribute('data-theme','dark');}}catch(e){}})();`,
          }}
        />
      </head>
      <body suppressHydrationWarning className="min-h-screen flex flex-col antialiased selection:bg-teal-500 selection:text-white relative transition-colors duration-200">
        {/* Ambient Glassmorphic Background Glow Orbs */}
        <div className="theme-bg-orbs fixed inset-0 pointer-events-none overflow-hidden -z-10 select-none">
          {/* Top-left Cyan / Teal Orb */}
          <div className="absolute -top-32 -left-32 w-[520px] h-[520px] bg-teal-500/15 rounded-full blur-[140px]" />
          {/* Top-right Sky / Blue Orb */}
          <div className="absolute top-24 -right-20 w-[600px] h-[600px] bg-sky-600/15 rounded-full blur-[160px]" />
          {/* Center-left Deep Indigo Glow */}
          <div className="absolute top-1/2 -left-40 w-[650px] h-[650px] bg-indigo-600/10 rounded-full blur-[180px]" />
          {/* Bottom-right Warm Amber Subtle Accent */}
          <div className="absolute bottom-10 right-10 w-[450px] h-[450px] bg-amber-500/10 rounded-full blur-[150px]" />
          {/* Fine geometric glass grid */}
          <div className="absolute inset-0 bg-[radial-gradient(rgba(255,255,255,0.05)_1px,transparent_1px)] [background-size:28px_28px] opacity-75" />
        </div>

        <PersistentDisclaimer />
        <Navbar />
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 pt-6 pb-12 relative z-10">
          {children}
        </main>
        <Footer />
      </body>
    </html>
  );
}
