import {
  FileText,
  Network,
  Clock,
  MessageSquare,
  BarChart2,
  Lock,
} from "lucide-react";

const features = [
  {
    icon: FileText,
    title: "Document Intelligence",
    description:
      "Automatically extract key facts, entities, and connections from FIRs, witness statements, and case files.",
  },
  {
    icon: Network,
    title: "Evidence Graph",
    description:
      "Visualize relationships between suspects, witnesses, locations, and events in an interactive knowledge graph.",
  },
  {
    icon: Clock,
    title: "Timeline Reconstruction",
    description:
      "Automatically build chronological event timelines to identify gaps, inconsistencies, and patterns.",
  },
  {
    icon: MessageSquare,
    title: "Investigator Copilot",
    description:
      "Ask questions in plain language. Get instant, sourced answers grounded in your uploaded case documents.",
  },
  {
    icon: BarChart2,
    title: "Case Analytics",
    description:
      "Priority scoring, risk assessment, and actionable insights to help officers focus on what matters most.",
  },
  {
    icon: Lock,
    title: "Secure & Compliant",
    description:
      "End-to-end encrypted, role-based access control, and full audit logging — built for law enforcement.",
  },
];

export function FeaturesSection() {
  return (
    <section
      id="features"
      className="mx-auto max-w-7xl px-6 py-20 sm:py-28"
      aria-labelledby="features-heading"
    >
      {/* Section header */}
      <div className="mb-14 text-center">
        <p className="mb-3 text-sm font-semibold uppercase tracking-widest text-primary">
          Capabilities
        </p>
        <h2
          id="features-heading"
          className="text-3xl font-extrabold tracking-tight text-foreground sm:text-4xl"
        >
          Everything an investigator needs
        </h2>
        <p className="mx-auto mt-4 max-w-xl text-muted-foreground">
          From raw documents to actionable intelligence — CrimeMind AI handles
          the heavy lifting so officers can focus on solving cases.
        </p>
      </div>

      {/* Feature grid */}
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {features.map(({ icon: Icon, title, description }) => (
          <article
            key={title}
            className="card-glass group rounded-2xl p-6 transition-all duration-300 hover:-translate-y-1 hover:border-primary/30 hover:shadow-lg hover:shadow-primary/10"
          >
            <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 transition-colors group-hover:bg-primary/20">
              <Icon
                size={22}
                className="text-primary"
                aria-hidden="true"
              />
            </div>
            <h3 className="mb-2 text-base font-bold text-foreground">
              {title}
            </h3>
            <p className="text-sm leading-relaxed text-muted-foreground">
              {description}
            </p>
          </article>
        ))}
      </div>
    </section>
  );
}
