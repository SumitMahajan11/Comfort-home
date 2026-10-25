"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Compass,
  MapPin,
  Sliders,
  Layers,
  Sparkles,
  Activity,
  HelpCircle,
  Search,
  Moon,
  Sun,
  Menu,
  X
} from "lucide-react";
import { CITIES_DATA } from "@/lib/constants";
import { CityKey } from "@/types";
import { CommandPalette } from "@/components/common/CommandPalette";

export const Navbar: React.FC = () => {
  const pathname = usePathname();
  const [isCommandOpen, setIsCommandOpen] = useState(false);
  const [isDark, setIsDark] = useState(true);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    try {
      const isHtmlLight = document.documentElement.classList.contains("light") || document.documentElement.getAttribute("data-theme") === "light";
      const saved = localStorage.getItem("theme");
      if (saved === "light" || isHtmlLight) {
        setIsDark(false);
        document.documentElement.classList.remove("dark");
        document.documentElement.classList.add("light");
        document.documentElement.setAttribute("data-theme", "light");
      } else {
        setIsDark(true);
        document.documentElement.classList.add("dark");
        document.documentElement.classList.remove("light");
        document.documentElement.setAttribute("data-theme", "dark");
      }
    } catch {}
  }, []);

  const toggleTheme = () => {
    const nextDark = !isDark;
    setIsDark(nextDark);
    if (nextDark) {
      document.documentElement.classList.add("dark");
      document.documentElement.classList.remove("light");
      document.documentElement.setAttribute("data-theme", "dark");
      try {
        localStorage.setItem("theme", "dark");
      } catch {}
    } else {
      document.documentElement.classList.remove("dark");
      document.documentElement.classList.add("light");
      document.documentElement.setAttribute("data-theme", "light");
      try {
        localStorage.setItem("theme", "light");
      } catch {}
    }
  };

  const navLinks = [
    { name: "Overview", href: "/", icon: <Activity className="w-4 h-4" /> },
    { name: "v2 Recommender", href: "/recommender", icon: <Sparkles className="w-4 h-4 text-teal-400" /> },
    { name: "City Explorer", href: "/cities", icon: <MapPin className="w-4 h-4" /> },
    { name: "Evaluate", href: "/evaluate", icon: <Sliders className="w-4 h-4" /> },
    { name: "Pareto Explorer", href: "/pareto", icon: <Layers className="w-4 h-4" /> },
    { name: "Explain", href: "/explain", icon: <Compass className="w-4 h-4" /> },
    { name: "Model Lab", href: "/models", icon: <Activity className="w-4 h-4" /> },
    { name: "About", href: "/about", icon: <HelpCircle className="w-4 h-4" /> },
  ];

  return (
    <>
      <header className="sticky top-0 z-30 w-full border-b border-white/10 bg-slate-950/60 backdrop-blur-2xl shadow-[0_4px_30px_rgba(0,0,0,0.35)]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          {/* Logo Brand */}
          <Link href="/" className="flex items-center space-x-2.5 group">
            <div className="p-2 rounded-xl bg-gradient-to-tr from-teal-500 to-cyan-400 text-slate-950 shadow-[0_0_20px_rgba(42,127,142,0.4)] group-hover:scale-105 transition">
              <Compass className="w-5 h-5 text-slate-950" />
            </div>
            <div>
              <span className="font-bold text-base tracking-tight text-white block">
                ClimateAdapt<span className="text-teal-400">-Comfort</span>
              </span>
              <span className="text-[10px] font-mono text-slate-400 block tracking-wide">
                Passive Shelter Decision-Support
              </span>
            </div>
          </Link>

          {/* Desktop Navigation Links */}
          <nav className="hidden xl:flex items-center space-x-1 p-1 rounded-xl bg-white/[0.03] border border-white/5 backdrop-blur-md">
            {navLinks.map((link) => {
              const isActive = pathname === link.href;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                    isActive
                      ? "bg-teal-500/20 text-teal-300 border border-teal-400/40 shadow-[0_0_15px_rgba(42,127,142,0.3),inset_0_1px_0_rgba(255,255,255,0.2)]"
                      : "text-slate-300 hover:text-white hover:bg-white/[0.06]"
                  }`}
                >
                  {link.icon}
                  <span>{link.name}</span>
                </Link>
              );
            })}
          </nav>

          {/* Actions: Command palette, print, theme, mobile toggle */}
          <div className="flex items-center space-x-2">
            {/* Search / Command trigger */}
            <button
              onClick={() => setIsCommandOpen(true)}
              className="flex items-center space-x-2 px-3 py-1.5 rounded-xl glass-button text-slate-300 hover:text-white transition text-xs shadow-inner"
              title="Search commands, cities, and models (Cmd+K)"
            >
              <Search className="w-3.5 h-3.5 text-teal-400" />
              <span className="hidden sm:inline">Search...</span>
              <kbd className="hidden sm:inline px-1.5 py-0.5 rounded bg-white/10 border border-white/15 text-[10px] font-mono text-slate-300">
                ⌘K
              </kbd>
            </button>

            {/* Dark/Light mode toggle */}
            <button
              onClick={toggleTheme}
              id="theme-toggle-btn"
              type="button"
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl glass-button text-xs font-medium cursor-pointer transition shadow-sm"
              title={isDark ? "Switch to Light Mode" : "Switch to Dark Mode"}
              aria-label="Toggle Dark and Light Mode"
            >
              {isDark ? (
                <>
                  <Sun className="w-4 h-4 text-amber-400" />
                  <span className="text-amber-200 hidden sm:inline font-mono">Light</span>
                </>
              ) : (
                <>
                  <Moon className="w-4 h-4 text-teal-700" />
                  <span className="text-slate-800 hidden sm:inline font-mono">Dark</span>
                </>
              )}
            </button>

            {/* Mobile menu button */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="xl:hidden p-2 rounded-xl glass-button text-slate-300"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>

        {/* Mobile Navigation Drawer */}
        {mobileMenuOpen && (
          <div className="xl:hidden border-t border-slate-800 bg-slate-950 px-4 pt-2 pb-4 space-y-1">
            {navLinks.map((link) => {
              const isActive = pathname === link.href;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`flex items-center space-x-2 px-3 py-2 rounded-lg text-sm font-medium transition ${
                    isActive
                      ? "bg-teal-500/15 text-teal-300 border border-teal-500/30"
                      : "text-slate-300 hover:bg-slate-800/50"
                  }`}
                >
                  {link.icon}
                  <span>{link.name}</span>
                </Link>
              );
            })}
          </div>
        )}
      </header>

      {/* Global Command Palette */}
      <CommandPalette
        isOpen={isCommandOpen}
        onClose={() => setIsCommandOpen(false)}
      />
    </>
  );
};
