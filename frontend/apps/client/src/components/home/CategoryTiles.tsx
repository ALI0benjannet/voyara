"use client";

import Link from "next/link";

import { ActivityImage } from "@/components/activities/ActivityImage";
import type { Category } from "@/features/catalog/api";
import { categoryName } from "@/features/catalog/i18n-content";
import { useHydratedTranslation } from "@/features/i18n/use-hydrated-language";
import { paths } from "@/routes/paths";

export type CategoryTile = { category: Category; count: number; photo: string | null };

/** Tuiles « Explorer par envie » : une par catégorie, avec une photo tirée
 *  du catalogue et le nombre d'activités. Le nom vient de la base, dans la
 *  langue active (repli français). */
export function CategoryTiles({ tiles }: { tiles: CategoryTile[] }) {
  const { t, language: lang } = useHydratedTranslation();
  return (
    <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
      {tiles.map(({ category, count, photo }) => {
        const name = categoryName(category, lang);
        return (
          <Link
            key={category.id}
            href={`${paths.activities}?cat=${category.id}`}
            className="group focus-visible:ring-primary relative block h-44 overflow-hidden rounded-2xl focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none sm:h-52"
            style={{ boxShadow: "var(--shadow-card)" }}
          >
            <div className="absolute inset-0 transition-transform duration-500 group-hover:scale-105">
              <ActivityImage src={photo} label={name} />
            </div>
            <div className="from-ink/85 via-ink/25 absolute inset-0 bg-gradient-to-t to-transparent" />
            <div className="absolute inset-x-0 bottom-0 p-4 text-white">
              <div className="font-display text-xl leading-tight sm:text-2xl">{name}</div>
              <div
                aria-hidden
                className="bg-gold mt-1.5 h-px w-8 transition-all duration-300 group-hover:w-14"
              />
              <div className="mt-1.5 text-sm text-white/85">{t("home.catCount", { count })}</div>
            </div>
          </Link>
        );
      })}
    </div>
  );
}
