"use client";

import { ActivityMapLoader } from "@/components/map/ActivityMapLoader";
import type { Activity } from "@/features/catalog/api";
import { activityTitle } from "@/features/catalog/i18n-content";
import { useHydratedTranslation } from "@/features/i18n/use-hydrated-language";

/** Section « Où se déroule l'activité » — titre traduit et mini-carte.
 *  Rendue uniquement quand l'activité est géolocalisée. */
export function ActivityLocation({ activity }: { activity: Activity }) {
  const { t, language } = useHydratedTranslation();

  if (activity.latitude == null || activity.longitude == null) return null;

  const title = t("detail.whereTitle");

  return (
    <section className="mt-9 max-w-2xl">
      <h2 className="font-display mb-3 text-2xl">{title}</h2>
      <div className="border-border h-72 overflow-hidden rounded-2xl border">
        <ActivityMapLoader
          points={[
            {
              id: activity.id,
              titre: activityTitle(activity, language),
              prix: activity.prix,
              localisation: activity.localisation,
              latitude: activity.latitude,
              longitude: activity.longitude,
            },
          ]}
          hint={`${title} — ${activity.localisation}`}
          className="size-full"
        />
      </div>
      <p className="text-muted-foreground mt-2 text-sm">{activity.localisation}</p>
    </section>
  );
}
