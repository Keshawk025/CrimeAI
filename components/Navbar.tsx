"use client";

import Link from "next/link";
import { Logo } from "@/components/Logo";
import { Button } from "@/components/ui/button";
import { useState } from "react";
import { Menu, X } from "lucide-react";
import { cn } from "@/lib/utils";

const navLinks = [
  { label: "Features", href: "#features" },
  { label: "How It Works", href: "#how-it-works" },
  { label: "About", href: "#about" },
];

export function Navbar() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 w-full border-b border-white/[0.06] bg-background/80 backdrop-blur-xl">
      <nav
        className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4"
        aria-label="Main navigation"
      >
        {/* Logo */}
        <Link href="/" className="flex items-center gap-3">
          <Logo size={36} />
          <span className="text-lg font-bold tracking-tight text-foreground">
            CrimeMind <span className="text-gradient-brand">AI</span>
          </span>
        </Link>

        {/* Desktop links */}
        <ul className="hidden items-center gap-8 md:flex" role="list">
          {navLinks.map((link) => (
            <li key={link.href}>
              <Link
                href={link.href}
                className="text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
              >
                {link.label}
              </Link>
            </li>
          ))}
        </ul>

        {/* CTA */}
        <div className="hidden md:flex">
          <Link href="/investigations/upload">
            <Button
              id="nav-cta-btn"
              size="sm"
              className="gradient-brand text-white shadow-lg transition-transform hover:scale-105 hover:opacity-90"
            >
              Start Investigation
            </Button>
          </Link>
        </div>

        {/* Mobile toggle */}
        <button
          id="mobile-menu-toggle"
          className="flex md:hidden text-muted-foreground"
          aria-label="Toggle mobile menu"
          onClick={() => setMobileOpen((v) => !v)}
        >
          {mobileOpen ? <X size={22} /> : <Menu size={22} />}
        </button>
      </nav>

      {/* Mobile menu */}
      <div
        className={cn(
          "md:hidden overflow-hidden transition-all duration-300",
          mobileOpen ? "max-h-64 py-4" : "max-h-0",
        )}
      >
        <ul className="flex flex-col gap-4 px-6" role="list">
          {navLinks.map((link) => (
            <li key={link.href}>
              <Link
                href={link.href}
                className="block text-sm font-medium text-muted-foreground hover:text-foreground"
                onClick={() => setMobileOpen(false)}
              >
                {link.label}
              </Link>
            </li>
          ))}
          <li className="pt-2">
            <Link href="/investigations/upload" onClick={() => setMobileOpen(false)} className="w-full">
              <Button
                id="mobile-cta-btn"
                size="sm"
                className="w-full gradient-brand text-white"
              >
                Start Investigation
              </Button>
            </Link>
          </li>
        </ul>
      </div>
    </header>
  );
}
