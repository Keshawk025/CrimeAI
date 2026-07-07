import { Button } from "@/components/ui/button";
import { Logo } from "@/components/Logo";
import { ArrowRight, Shield, Brain, Search } from "lucide-react";
import Link from "next/link";

const badges = [
  { icon: Shield, label: "Karnataka Police" },
  { icon: Brain, label: "AI-Powered" },
  { icon: Search, label: "Smart Evidence" },
];

export function HeroSection() {
  return (
    <section
      id="hero"
      className="relative flex flex-1 flex-col items-center justify-center overflow-hidden px-6 py-24 text-center sm:py-32"
    >
      {/* Background grid */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage:
            "linear-gradient(oklch(0.95 0 0) 1px, transparent 1px), linear-gradient(90deg, oklch(0.95 0 0) 1px, transparent 1px)",
          backgroundSize: "48px 48px",
        }}
      />

      {/* Glowing orb */}
      <div
        aria-hidden="true"
        className="animate-pulse-glow pointer-events-none absolute left-1/2 top-0 h-96 w-96 -translate-x-1/2 -translate-y-1/2 rounded-full opacity-25"
        style={{
          background:
            "radial-gradient(circle, oklch(0.62 0.22 25) 0%, transparent 70%)",
        }}
      />

      {/* Logo */}
      <div className="animate-float mb-8">
        <Logo size={80} />
      </div>

      {/* Badge strip */}
      <div className="mb-6 flex flex-wrap items-center justify-center gap-3">
        {badges.map(({ icon: Icon, label }) => (
          <span
            key={label}
            className="card-glass inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium text-muted-foreground"
          >
            <Icon size={12} className="text-primary" aria-hidden="true" />
            {label}
          </span>
        ))}
      </div>

      {/* Heading */}
      <h1 className="mb-4 max-w-3xl text-5xl font-extrabold leading-tight tracking-tight sm:text-6xl lg:text-7xl">
        <span className="text-foreground">CrimeMind</span>{" "}
        <span className="text-gradient-brand">AI</span>
      </h1>

      {/* Subtitle */}
      <p className="mb-3 text-lg font-semibold text-muted-foreground sm:text-xl">
        AI Investigation Copilot for Karnataka Police
      </p>
      <p className="mb-10 max-w-xl text-base text-muted-foreground/80">
        Accelerate case resolution with intelligent document analysis, timeline
        reconstruction, and AI-driven evidence correlation — purpose-built for
        law enforcement.
      </p>

      {/* CTA */}
      <div className="flex flex-col items-center gap-4 sm:flex-row">
        <Link href="/investigations/upload">
          <Button
            id="hero-cta-primary"
            size="lg"
            className="gradient-brand glow-brand px-8 py-6 text-base font-semibold text-white transition-transform hover:scale-105 hover:opacity-90"
          >
            Start an Investigation
            <ArrowRight className="ml-2 h-5 w-5" aria-hidden="true" />
          </Button>
        </Link>
        <Button
          id="hero-cta-secondary"
          size="lg"
          variant="outline"
          className="border-white/10 px-8 py-6 text-base font-semibold text-foreground backdrop-blur hover:bg-white/5"
        >
          Learn More
        </Button>
      </div>

      {/* Stats strip */}
      <div className="mt-16 flex flex-wrap justify-center gap-10">
        {[
          { value: "10×", label: "Faster Analysis" },
          { value: "98%", label: "Evidence Recall" },
          { value: "24/7", label: "AI Availability" },
        ].map((stat) => (
          <div key={stat.label} className="text-center">
            <p className="text-3xl font-extrabold text-gradient-brand">
              {stat.value}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">{stat.label}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
