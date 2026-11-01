"use client";

import React, { useState, useEffect, useRef } from "react";
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
import { CommandPalette } from "@/components/common/CommandPalette";

export const Navbar: React.FC = () => {
  const pathname = usePathname();
  const [isCommandOpen, setIsCommandOpen] = useState(false);
  const [isDark, setIsDark] = useState(true);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [shortcutKey, setShortcutKey] = useState("⌘K");

  const drawerRef = useRef<HTMLDivElement>(null);
  const hamburgerBtnRef = useRef<HTMLButtonElement>(null);

  // Initialize theme from localStorage or prefers-color-scheme
  useEffect(() => {
    try {
      const saved = localStorage.getItem("theme");
      const isHtmlDark =
        document.documentElement.classList.contains("dark") ||
        document.documentElement.getAttribute("data-theme") === "dark";
      const prefersDark =
        typeof window !== "undefined" &&
        window.matchMedia("(prefers-color-scheme: dark)").matches;
      const isDarkMode = saved ? saved === "dark" : (isHtmlDark || prefersDark);
      setIsDark(isDarkMode);
    } catch {}
  }, []);

  // Detect OS for shortcut hint (macOS ⌘K vs Windows/Linux Ctrl K)
  useEffect(() => {
    try {
      const nav = navigator as unknown as { userAgentData?: { platform?: string }; platform?: string; userAgent?: string };
      const platform = nav.userAgentData?.platform || nav.platform || nav.userAgent || "";
      const isMac = /mac/i.test(platform);
      setShortcutKey(isMac ? "⌘K" : "Ctrl K");
    } catch {
      setShortcutKey("Ctrl K");
    }
  }, []);

  // Focus trap and Escape listener for mobile/tablet drawer
  useEffect(() => {
    if (!mobileMenuOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        setMobileMenuOpen(false);
        hamburgerBtnRef.current?.focus();
        return;
      }

      if (e.key === "Tab" && drawerRef.current) {
        const focusableElements = drawerRef.current.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])'
        );
        if (focusableElements.length === 0) return;
        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];

        if (e.shiftKey) {
          if (document.activeElement === firstElement) {
            e.preventDefault();
            lastElement.focus();
          }
        } else {
          if (document.activeElement === lastElement) {
            e.preventDefault();
            firstElement.focus();
          }
        }
      }
    };

    // Auto-focus first focusable element inside drawer
    const timer = setTimeout(() => {
      if (drawerRef.current) {
        const first = drawerRef.current.querySelector<HTMLElement>(
          'button, a[href], [tabindex]:not([tabindex="-1"])'
        );
        first?.focus();
      }
    }, 50);

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      clearTimeout(timer);
    };
  }, [mobileMenuOpen]);

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
    { name: "Overview", href: "/", icon: <Activity className="w-3.5 h-3.5" /> },
    { name: "Plan", href: "/recommender", icon: <Sparkles className="w-3.5 h-3.5 text-teal-400 light:text-teal-600" /> },
    { name: "Cities", href: "/cities", icon: <MapPin className="w-3.5 h-3.5" /> },
    { name: "Evaluate", href: "/evaluate", icon: <Sliders className="w-3.5 h-3.5" /> },
    { name: "Trade-offs", href: "/pareto", icon: <Layers className="w-3.5 h-3.5" /> },
    { name: "Explain", href: "/explain", icon: <Compass className="w-3.5 h-3.5" /> },
    { name: "Models", href: "/models", icon: <Activity className="w-3.5 h-3.5" /> },
    { name: "About", href: "/about", icon: <HelpCircle className="w-3.5 h-3.5" /> },
  ];

  return (
    <>
      <header className="sticky top-0 z-30 w-full h-16 min-h-[64px] max-h-[64px] border-b border-[var(--line)] bg-[var(--surface)] text-[var(--ink)] shadow-sm transition-colors duration-200">
        <div className="max-w-[1280px] w-full mx-auto px-4 sm:px-6 h-16 flex items-center justify-between overflow-hidden">
          {/* Logo Brand */}
          <Link
            href="/"
            className="flex items-center space-x-2.5 group shrink-0 h-10"
            aria-label="ClimateAdapt-Comfort Home"
          >
            <div className="p-1.5 rounded-[8px] bg-[var(--primary)] text-white shadow-sm group-hover:opacity-90 transition shrink-0 flex items-center justify-center">
              <Compass className="w-5 h-5 text-white" />
            </div>
            <div className="flex items-center whitespace-nowrap">
              <span className="font-bold text-base tracking-tight text-[var(--ink)] whitespace-nowrap">
                ClimateAdapt-Comfort
              </span>
              <span className="hidden min-[1280px]:inline text-xs text-[var(--ink-2)] ml-2.5 pl-2.5 border-l border-[var(--line)] whitespace-nowrap">
                Passive Shelter Decision-Support
              </span>
            </div>
          </Link>

          {/* Desktop Navigation Links (>=1100px) */}
          <nav
            className="hidden min-[1100px]:flex items-center space-x-0.5 p-1 rounded-[8px] bg-[var(--surface-2)] border border-[var(--line)]"
            aria-label="Main Navigation"
          >
            {navLinks.map((link) => {
              const isActive = pathname === link.href;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`flex items-center space-x-1.5 px-2.5 py-1.5 rounded-[6px] text-xs font-medium whitespace-nowrap transition ${
                    isActive
                      ? "bg-[var(--surface)] text-[var(--ink)] border border-[var(--line)] shadow-sm font-semibold"
                      : "text-[var(--ink-2)] hover:text-[var(--ink)] hover:bg-[var(--surface)]/50"
                  }`}
                >
                  {link.icon}
                  <span className="whitespace-nowrap">{link.name}</span>
                </Link>
              );
            })}
          </nav>

          {/* Right Actions: Search trigger, Theme toggle, Hamburger menu */}
          <div className="flex items-center space-x-2 shrink-0">
            {/* Search / Command trigger */}
            <button
              onClick={() => setIsCommandOpen(true)}
              className="flex items-center space-x-2 px-3 py-1.5 rounded-[8px] bg-[var(--surface-2)] border border-[var(--line)] text-[var(--ink-2)] hover:text-[var(--ink)] transition text-xs"
              title={`Search commands, cities, and models (${shortcutKey})`}
              aria-label={`Search (${shortcutKey})`}
            >
              <Search className="w-3.5 h-3.5 text-[var(--ink-2)]" />
              <span className="hidden sm:inline whitespace-nowrap">Search...</span>
              <kbd className="hidden sm:inline px-1.5 py-0.5 rounded bg-[var(--surface)] border border-[var(--line)] text-[10px] text-[var(--ink-2)] tabular-nums">
                {shortcutKey}
              </kbd>
            </button>

            {/* Dark/Light mode toggle */}
            <button
              onClick={toggleTheme}
              id="theme-toggle-btn"
              type="button"
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-[8px] bg-[var(--surface-2)] border border-[var(--line)] text-xs font-medium cursor-pointer transition shadow-sm text-[var(--ink)] hover:bg-[var(--surface)]"
              title={isDark ? "Switch to light theme" : "Switch to dark theme"}
              aria-label={isDark ? "Switch to light theme" : "Switch to dark theme"}
            >
              {isDark ? (
                <>
                  <Moon className="w-4 h-4 text-[var(--primary)]" aria-hidden="true" />
                  <span className="text-[var(--ink)] hidden sm:inline text-xs font-medium">Dark theme</span>
                </>
              ) : (
                <>
                  <Sun className="w-4 h-4 text-[var(--warn)]" aria-hidden="true" />
                  <span className="text-[var(--ink)] hidden sm:inline text-xs font-medium">Light theme</span>
                </>
              )}
            </button>

            {/* Hamburger menu button (< 1100px) */}
            <button
              ref={hamburgerBtnRef}
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="min-[1100px]:hidden p-2 rounded-[8px] bg-[var(--surface-2)] border border-[var(--line)] text-[var(--ink)] hover:bg-[var(--surface)]"
              aria-expanded={mobileMenuOpen}
              aria-controls="mobile-nav-drawer"
              aria-label={mobileMenuOpen ? "Close navigation menu" : "Open navigation menu"}
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>

        {/* Mobile/Tablet Navigation Drawer (< 1100px) */}
        {mobileMenuOpen && (
          <div
            id="mobile-nav-drawer"
            role="dialog"
            aria-modal="true"
            aria-label="Site Navigation"
            className="fixed inset-0 z-50 min-[1100px]:hidden"
          >
            {/* Backdrop overlay */}
            <div
              className="fixed inset-0 bg-black/40 backdrop-blur-sm transition-opacity"
              onClick={() => {
                setMobileMenuOpen(false);
                hamburgerBtnRef.current?.focus();
              }}
              aria-hidden="true"
            />

            {/* Drawer content */}
            <div
              ref={drawerRef}
              className="fixed top-0 right-0 bottom-0 w-72 sm:w-80 bg-[var(--surface)] border-l border-[var(--line)] shadow-lg p-5 flex flex-col justify-between overflow-y-auto z-10"
            >
              <div className="space-y-4">
                {/* Drawer Header */}
                <div className="flex items-center justify-between pb-3 border-b border-[var(--line)]">
                  <div className="flex items-center space-x-2">
                    <div className="p-1.5 rounded-[8px] bg-[var(--primary)] text-white">
                      <Compass className="w-4 h-4" />
                    </div>
                    <span className="font-bold text-sm text-[var(--ink)]">Navigation</span>
                  </div>
                  <button
                    onClick={() => {
                      setMobileMenuOpen(false);
                      hamburgerBtnRef.current?.focus();
                    }}
                    className="p-1.5 rounded-[8px] text-[var(--ink-2)] hover:text-[var(--ink)] hover:bg-[var(--surface-2)]"
                    aria-label="Close navigation menu"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>

                {/* Navigation Links */}
                <nav className="space-y-1">
                  {navLinks.map((link) => {
                    const isActive = pathname === link.href;
                    return (
                      <Link
                        key={link.href}
                        href={link.href}
                        onClick={() => {
                          setMobileMenuOpen(false);
                          hamburgerBtnRef.current?.focus();
                        }}
                        className={`flex items-center space-x-2.5 px-3 py-2.5 rounded-[8px] text-sm font-medium whitespace-nowrap transition ${
                          isActive
                            ? "bg-[var(--surface-2)] text-[var(--ink)] border border-[var(--line)] font-semibold"
                            : "text-[var(--ink-2)] hover:text-[var(--ink)] hover:bg-[var(--surface-2)]/60"
                        }`}
                      >
                        {link.icon}
                        <span className="whitespace-nowrap">{link.name}</span>
                      </Link>
                    );
                  })}
                </nav>
              </div>

              {/* Drawer Footer info */}
              <div className="pt-4 border-t border-[var(--line)] text-xs text-[var(--ink-2)] space-y-1">
                <p className="font-semibold text-[var(--ink)]">ClimateAdapt-Comfort</p>
                <p className="text-[11px]">Passive Shelter Decision-Support</p>
              </div>
            </div>
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
