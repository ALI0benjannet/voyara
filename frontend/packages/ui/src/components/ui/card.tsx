import type { ReactNode } from "react";
import { cn } from "@voyara/ui/lib/utils";

export function Card({ className, children }: { className?: string; children: ReactNode }) {
  return (
    <section
      // `card-elevated` centralise l'ombre et l'élévation au survol : une
      // seule définition dans `styles.css`, réutilisée par toutes les cartes.
      className={cn("card-elevated border-border bg-card rounded-2xl border", className)}
    >
      {children}
    </section>
  );
}

export function CardHeader({
  title,
  description,
  action,
}: {
  title: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="border-border flex items-start justify-between gap-4 border-b p-6">
      <div className="space-y-1">
        <h2 className="text-foreground text-lg font-semibold tracking-tight">{title}</h2>
        {description && <p className="text-muted-foreground text-sm">{description}</p>}
      </div>
      {action}
    </div>
  );
}

export function CardBody({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={cn("p-6", className)}>{children}</div>;
}
