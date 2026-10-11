import type { ReactNode } from "react";
import { cn } from "@voyara/ui/lib/utils";

type Props = {
  icon?: ReactNode;
  title: ReactNode;
  subtitle?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
  className?: string;
};

export function AuthCard({ icon, title, subtitle, children, footer, className }: Props) {
  return (
    <main className="relative flex min-h-dvh items-center justify-center overflow-hidden p-6 sm:p-8">
      {/* décor de fond */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(60rem_40rem_at_50%_-10%,rgba(148,163,184,.35),transparent)]"
      />
      <div
        className={cn(
          "border-border bg-card/90 w-full max-w-md space-y-6 rounded-3xl border p-8",
          "shadow-[0_20px_60px_-25px_rgba(15,23,42,.45)] backdrop-blur-xl",
          className,
        )}
      >
        <header className="space-y-4">
          {icon && (
            <div className="bg-primary flex size-12 items-center justify-center rounded-2xl text-white shadow-sm">
              {icon}
            </div>
          )}
          <div className="space-y-1.5">
            <h1 className="text-foreground text-2xl font-semibold tracking-tight">{title}</h1>
            {subtitle && (
              <p className="text-muted-foreground text-sm leading-relaxed">{subtitle}</p>
            )}
          </div>
        </header>

        {children}

        {footer && <div className="text-muted-foreground pt-1 text-center text-sm">{footer}</div>}
      </div>
    </main>
  );
}
