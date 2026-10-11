"use client";

import Link from "next/link";

import { ActivityImage } from "@/components/activities/ActivityImage";
import { FavoriteButton } from "@/components/activities/FavoriteButton";
import type { Activity } from "@/features/catalog/api";
import { formatDuration, formatPrice } from "@/features/catalog/format";
import { activityTitle, categoryName } from "@/features/catalog/i18n-content";
import { useHydratedTranslation } from "@/features/i18n/use-hydrated-language";

export type Rating = { average: number; count: number };

/**
 * Carte activité. Le titre et la catégorie viennent de la base : ils sont lus
 * dans la langue active (colonnes `*_en` / `*_ar`, repli français), tandis que
 * les libellés d'interface passent par i18next.
 */
export function ActivityCard({ activity, rating }: { activity: Activity; rating?: Rating }) {
  // Langue figée sur le français jusqu'à l'hydratation (cohérence SSR/client).
  const { t, language: lang } = useHydratedTranslation();
  const detailPath = `/activities/${activity.id}`;
  const title = activityTitle(activity, lang);

  return (
    <article className="card-elevated group border-border bg-card focus-within:ring-primary relative flex flex-col overflow-hidden rounded-2xl border focus-within:ring-2 focus-within:ring-offset-2">
      {/* Lien étalé sur toute la carte : un clic n'importe où ouvre l'activité.
          Un seul lien porte le titre accessible — imbriquer des <a> serait
          invalide, et les autres éléments cliquables (cœur, bouton) repassent
          au-dessus via `relative z-10`. */}
      <Link href={detailPath} className="absolute inset-0 z-0" aria-label={title}>
        <span className="sr-only">{title}</span>
      </Link>

      <div className="pointer-events-none relative h-44">
        <ActivityImage src={activity.photos} label={`Photo — ${activity.localisation}`} />
        <FavoriteButton activityId={activity.id} />
        {activity.category && (
          // Terracotta : identifie la catégorie sans concurrencer le bleu des
          // actions. Blanc sur ce fond = 4.6:1, conforme AA.
          <span className="bg-accent/95 text-accent-foreground absolute start-3 bottom-3 rounded-full px-3 py-1 text-xs font-semibold shadow-sm backdrop-blur-sm">
            {categoryName(activity.category, lang)}
          </span>
        )}
      </div>

      <div className="pointer-events-none relative z-10 flex flex-1 flex-col gap-1.5 p-4">
        <h3 className="font-display text-foreground group-hover:text-primary text-lg leading-snug transition-colors">
          {title}
        </h3>
        <div className="text-muted-foreground text-[13px]">
          {activity.localisation} · {formatDuration(activity.duree, lang)}
        </div>
        {rating && rating.count > 0 && (
          <div className="text-foreground/75 text-[13px]">
            <span className="text-gold-ink">★</span> <b>{rating.average.toFixed(1)}</b> (
            {rating.count})
          </div>
        )}
        <div className="mt-auto flex items-center justify-between pt-2">
          <div>
            <span className="text-lg font-bold">{formatPrice(activity.prix)}</span>
            <span className="text-muted-foreground text-xs"> {t("catalog.perPerson")}</span>
          </div>
          <Link
            href={detailPath}
            tabIndex={-1}
            aria-hidden
            className="bg-primary text-primary-foreground hover:bg-primary-hover pointer-events-auto relative z-10 rounded-full px-4 py-2 text-[13px] font-semibold transition-colors"
          >
            {t("catalog.book")}
          </Link>
        </div>
      </div>
    </article>
  );
}
