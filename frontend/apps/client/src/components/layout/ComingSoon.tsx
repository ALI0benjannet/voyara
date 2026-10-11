import Link from "next/link";
import type { LucideIcon } from "lucide-react";

import { T } from "@/components/i18n/T";
import { paths } from "@/routes/paths";

/** Page d'attente des onglets non encore réservables (séjours, vols, voitures,
 *  transferts). Les tables existent déjà côté catalog-service ; l'API viendra. */
export function ComingSoon({
  icon: Icon,
  titleKey,
  subKey,
}: {
  icon: LucideIcon;
  titleKey: string;
  subKey: string;
}) {
  return (
    <main className="mx-auto flex max-w-2xl flex-col items-center px-4 py-24 text-center sm:px-8">
      <div className="bg-primary/10 text-primary mb-6 flex size-16 items-center justify-center rounded-2xl">
        <Icon className="size-8" strokeWidth={1.6} />
      </div>
      <span className="border-gold/40 text-primary-hover mb-4 rounded-full border px-3 py-1 text-xs font-semibold tracking-[0.14em] uppercase">
        <T k="comingSoon.badge" />
      </span>
      <h1 className="font-display text-primary-hover mb-3 text-4xl">
        <T k={titleKey} />
      </h1>
      <p className="text-muted-foreground mb-2 text-lg">
        <T k={subKey} />
      </p>
      <p className="text-muted-foreground mb-8">
        <T k="comingSoon.body" />
      </p>
      <Link
        href={paths.activities}
        className="bg-primary text-primary-foreground hover:bg-primary-hover focus-visible:ring-primary rounded-lg px-5 py-2.5 text-sm font-semibold transition-colors focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none"
      >
        <T k="comingSoon.cta" />
      </Link>
    </main>
  );
}
