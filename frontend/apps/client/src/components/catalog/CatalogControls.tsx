"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { MapPin, X } from "lucide-react";

import { cn } from "@voyara/ui/lib/utils";

import type { Category } from "@/features/catalog/api";
import { categoryName } from "@/features/catalog/i18n-content";
import { useHydratedTranslation } from "@/features/i18n/use-hydrated-language";

/** Contrôles du catalogue (recherche, catégories, ville, tri, vue) — écrivent
 *  dans l'URL ; la liste elle-même est re-rendue côté serveur à chaque
 *  changement, ce qui garde chaque combinaison de filtres partageable. */
export function CatalogControls({
  categories,
  cities,
}: {
  categories: Category[];
  cities: string[];
}) {
  const { t, language } = useHydratedTranslation();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const search = searchParams?.get("search") ?? "";
  const cat = searchParams?.get("cat");
  const city = searchParams?.get("city") ?? "";
  const sort = searchParams?.get("sort") ?? "pop";
  const view = searchParams?.get("view") ?? "grid";

  const setParams = (patch: Record<string, string | null>) => {
    const next = new URLSearchParams(searchParams?.toString());
    for (const [key, value] of Object.entries(patch)) {
      if (value) next.set(key, value);
      else next.delete(key);
    }
    router.replace(`${pathname}?${next.toString()}`, { scroll: false });
  };

  const hasFilters = Boolean(search || cat || city);

  const segClass = (active: boolean) =>
    cn(
      "px-4 py-2 text-[13px] font-semibold transition-colors",
      active ? "bg-ink text-background" : "bg-card text-muted-foreground hover:text-foreground",
    );

  const chipClass = (active: boolean) =>
    cn(
      "rounded-full border px-4 py-2 text-sm font-semibold transition-colors",
      active
        ? "border-primary bg-primary text-primary-foreground shadow-sm"
        : "border-input bg-card text-foreground/75 hover:border-primary hover:bg-primary/5 hover:text-primary",
    );

  return (
    <>
      <div className="flex items-center gap-2.5">
        <select
          value={sort}
          onChange={(e) => setParams({ sort: e.target.value === "pop" ? null : e.target.value })}
          aria-label={t("catalog.sortPop")}
          className="border-input bg-card rounded-full border px-4 py-2 text-sm"
        >
          <option value="pop">{t("catalog.sortPop")}</option>
          <option value="asc">{t("catalog.sortAsc")}</option>
          <option value="desc">{t("catalog.sortDesc")}</option>
        </select>
        <div className="border-input flex overflow-hidden rounded-full border">
          <button
            type="button"
            onClick={() => setParams({ view: null })}
            className={segClass(view === "grid")}
          >
            {t("catalog.viewGrid")}
          </button>
          <button
            type="button"
            onClick={() => setParams({ view: "map" })}
            className={segClass(view === "map")}
          >
            {t("catalog.viewMap")}
          </button>
        </div>
      </div>

      <div className="my-6 flex w-full flex-col gap-3">
        {/* Recherche libre + ville */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative">
            <MapPin className="text-foreground/40 pointer-events-none absolute start-4 top-1/2 size-4 -translate-y-1/2" />
            <select
              value={city}
              onChange={(e) => setParams({ city: e.target.value || null })}
              aria-label={t("catalog.allCities")}
              className="border-input bg-card appearance-none rounded-full border py-2.5 ps-11 pe-6 text-sm"
            >
              <option value="">{t("catalog.allCities")}</option>
              {cities.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          </div>

          {hasFilters && (
            <button
              type="button"
              onClick={() => setParams({ search: null, cat: null, city: null })}
              className="border-input text-muted-foreground hover:border-primary hover:bg-primary/5 hover:text-primary inline-flex items-center gap-1.5 rounded-full border px-4 py-2.5 text-sm font-semibold transition-colors"
            >
              <X className="size-4" />
              {t("catalog.reset")}
            </button>
          )}
        </div>

        {/* Catégories */}
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => setParams({ cat: null })}
            className={chipClass(!cat)}
          >
            {t("catalog.allCategories")}
          </button>
          {categories.map((category) => (
            <button
              key={category.id}
              type="button"
              onClick={() => setParams({ cat: String(category.id) })}
              className={chipClass(cat === String(category.id))}
            >
              {categoryName(category, language)}
            </button>
          ))}
        </div>
      </div>
    </>
  );
}
