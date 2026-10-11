"use client";

import { Heart } from "lucide-react";

import { cn } from "@voyara/ui/lib/utils";

import { useToggleFavorite } from "@/features/favorites/hooks";
import { useHydratedTranslation } from "@/features/i18n/use-hydrated-language";

/** Îlot client : cœur favori posé sur les cartes/pages rendues côté serveur. */
export function FavoriteButton({
  activityId,
  size = "sm",
}: {
  activityId: number;
  size?: "sm" | "lg";
}) {
  const { isFavorite, toggle } = useToggleFavorite();
  const { t } = useHydratedTranslation();
  const fav = isFavorite(activityId);

  return (
    <button
      type="button"
      aria-label={t("catalog.favorite")}
      aria-pressed={fav}
      onClick={(e) => {
        e.preventDefault();
        e.stopPropagation();
        toggle(activityId);
      }}
      className={cn(
        // `z-10` : passe au-dessus du lien étalé des cartes d'activité.
        "bg-card/95 pointer-events-auto absolute end-3 top-3 z-10 flex items-center justify-center rounded-full shadow-md transition-transform hover:scale-105",
        size === "lg" ? "size-11" : "size-9",
        fav ? "text-accent" : "text-foreground/35",
      )}
    >
      <Heart className={size === "lg" ? "size-5" : "size-4"} fill={fav ? "currentColor" : "none"} />
    </button>
  );
}
