import { cn } from "@/lib/utils";

interface LogoProps {
  size?: number;
  className?: string;
}

export function Logo({ size = 40, className }: LogoProps) {
  return (
    <div
      className={cn(
        "relative flex items-center justify-center rounded-xl gradient-brand glow-brand",
        className,
      )}
      style={{ width: size, height: size }}
      aria-label="CrimeMind AI logo"
      role="img"
    >
      {/* Shield icon SVG */}
      <svg
        width={size * 0.6}
        height={size * 0.6}
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        <path
          d="M12 2L4 6V12C4 16.418 7.582 20.471 12 22C16.418 20.471 20 16.418 20 12V6L12 2Z"
          fill="white"
          fillOpacity="0.95"
        />
        <path
          d="M9 12L11 14L15 10"
          stroke="#e53e3e"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </div>
  );
}
