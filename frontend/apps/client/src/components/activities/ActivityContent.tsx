"use client";

import type { Activity } from "@/features/catalog/api";
import { activityDescription, activityTitle, categoryName } from "@/features/catalog/i18n-content";
import { formatDuration } from "@/features/catalog/format";
import { useHydratedTranslation } from "@/features/i18n/use-hydrated-language";

/** Titre, catégorie et description de l'activité, dans la langue de l'interface.
 *
 *  Ce contenu vient de la base : il ne peut pas être traduit par les fichiers
 *  i18n statiques. Le composant est rendu côté client parce que la langue est
 *  un choix du navigateur — mais le HTML servi par le serveur contient déjà la
 *  version française, qui reste celle indexée par les moteurs de recherche. */
export function ActivityContent({
  activity,
  stats,
}: {
  activity: Activity;
  stats?: { average: number; count: number };
}) {
  const { t, language: lang } = useHydratedTranslation();

  return (
    <>
      {activity.category && (
        // Terracotta en aplat léger : cohérent avec le badge des cartes.
        <span className="bg-accent/12 text-accent-hover inline-block rounded-full px-3.5 py-1.5 text-[13px] font-semibold">
          {categoryName(activity.category, lang)}
        </span>
      )}
      <h1 className="font-display text-primary-hover mt-4 mb-2.5 text-3xl leading-tight sm:text-4xl">
        {activityTitle(activity, lang)}
      </h1>
      <div className="text-muted-foreground mb-2 flex flex-wrap items-center gap-x-2.5 gap-y-1 text-[15px]">
        <span>{activity.localisation}</span>
        <span aria-hidden className="bg-gold size-1 rounded-full" />
        <span>{formatDuration(activity.duree, lang)}</span>
      </div>
      {stats && stats.count > 0 && (
        <div className="mb-6 flex items-center gap-1.5 text-[15px]">
          {/* `gold-ink` : l'or vif tombe à 2:1 sur fond clair, illisible ici. */}
          <span className="text-gold-ink">★</span>
          <b>{stats.average.toFixed(1)}</b>
          <span className="text-muted-foreground">
            · {t("detail.reviewCount", { count: stats.count })}
          </span>
        </div>
      )}
      {/* Filet doré vertical : marque la description comme un bloc éditorial. */}
      <p className="border-gold/40 text-foreground/80 max-w-2xl border-s-2 ps-4 text-base leading-relaxed">
        {activityDescription(activity, lang)}
      </p>
    </>
  );
}
