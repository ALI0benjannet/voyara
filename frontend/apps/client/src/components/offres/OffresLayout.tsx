import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { T } from "@/components/i18n/T";

/** Gabarit commun des pages Séjours, Vols, Voitures et Transferts : titre,
 *  nombre d'offres, filtres, grille ou état vide. Rendu côté serveur (SEO). */
export function OffresLayout({
  icon: Icon,
  titleKey,
  subKey,
  count,
  basePath,
  filters,
  children,
}: {
  icon: LucideIcon;
  titleKey: string;
  subKey: string;
  count: number;
  basePath: string;
  filters?: ReactNode;
  children: ReactNode;
}) {
  return (
    <main className="mx-auto max-w-7xl px-4 py-10 sm:px-8">
      <div className="mb-6 flex flex-wrap items-start gap-4">
        <div className="bg-primary/10 text-primary flex size-12 shrink-0 items-center justify-center rounded-xl">
          <Icon className="size-6" strokeWidth={1.6} />
        </div>
        <div>
          <h1 className="font-display text-primary-hover text-4xl">
            <T k={titleKey} />
          </h1>
          <div aria-hidden className="bg-gold mt-2 h-px w-14" />
          <p className="text-muted-foreground mt-2">
            <T k={subKey} /> · <T k="offres.count" values={{ count }} />
          </p>
        </div>
      </div>

      {filters && <div className="mb-8 flex flex-col gap-3">{filters}</div>}

      {count === 0 ? (
        <div className="border-input bg-card rounded-2xl border border-dashed px-5 py-16 text-center">
          <div
            aria-hidden
            className="border-gold-ink/50 mx-auto mb-5 size-3.5 rotate-45 rounded-[3px] border-2"
          />
          <div className="text-muted-foreground mb-5">
            <T k="offres.empty" />
          </div>
          <Link
            href={basePath}
            className="bg-primary text-primary-foreground hover:bg-primary-hover inline-block rounded-full px-6 py-3 font-semibold transition-colors"
          >
            <T k="offres.reset" />
          </Link>
        </div>
      ) : (
        children
      )}

      <p className="text-muted-foreground mt-10 text-center text-xs">
        <T k="offres.demoNote" />
      </p>
    </main>
  );
}

/** Puces de filtre en liens (fonctionnent sans JavaScript, indexables). */
export function FilterChips({
  labelKey,
  param,
  options,
  current,
  basePath,
  params,
}: {
  labelKey: string;
  param: string;
  /** `label` affiché tel quel (ville), ou `labelKey` traduit. */
  options: { value: string; label?: string; labelKey?: string }[];
  current?: string;
  basePath: string;
  /** Autres filtres actifs, conservés dans les liens. */
  params: Record<string, string | undefined>;
}) {
  const href = (value?: string) => {
    const qs = new URLSearchParams();
    for (const [key, v] of Object.entries(params)) if (v && key !== param) qs.set(key, v);
    if (value) qs.set(param, value);
    return qs.size ? `${basePath}?${qs}` : basePath;
  };
  const chip = (active: boolean) =>
    `rounded-full border px-3.5 py-1.5 text-sm font-medium transition-colors ${
      active
        ? "bg-primary border-primary text-primary-foreground"
        : "border-border bg-card text-foreground/80 hover:border-primary hover:text-primary"
    }`;

  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-muted-foreground me-1 text-sm font-semibold">
        <T k={labelKey} />
      </span>
      <Link href={href()} className={chip(!current)}>
        <T k="offres.all" />
      </Link>
      {options.map((o) => (
        <Link key={o.value} href={href(o.value)} className={chip(current === o.value)}>
          {o.labelKey ? <T k={o.labelKey} /> : o.label}
        </Link>
      ))}
    </div>
  );
}

/** Badge « Réservation en ligne bientôt » : les offres ne sont pas encore
 *  branchées au tunnel booking + paiement (seules les activités le sont). */
export function BookSoonBadge() {
  return (
    <span className="border-gold/50 text-primary-hover rounded-full border px-3 py-1.5 text-[12px] font-semibold">
      <T k="offres.bookSoon" />
    </span>
  );
}
