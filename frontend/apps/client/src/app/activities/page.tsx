import { Suspense } from "react";
import type { Metadata } from "next";
import Link from "next/link";

import { ActivityCard } from "@/components/activities/ActivityCard";
import { T } from "@/components/i18n/T";
import { CatalogControls } from "@/components/catalog/CatalogControls";
import { ActivityMapLoader } from "@/components/map/ActivityMapLoader";
import type { MapPoint } from "@/components/map/ActivityMap";
import type { Activity } from "@/features/catalog/api";
import { fetchActivities, fetchCategories, fetchReviewStats } from "@/lib/server-api";

export const metadata: Metadata = {
  title: "Activités",
  description:
    "Toutes les activités touristiques à réserver en Tunisie : mer, désert, culture, aventure et gastronomie. Filtrez par région, catégorie et prix.",
  alternates: { canonical: "/activities" },
};

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

const first = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v);

/** Ne garde que les activités géolocalisées — les autres n'ont rien à faire
 *  sur la carte (l'ancienne vue stylisée les plaçait arbitrairement). */
function mapPoints(activities: Activity[]): MapPoint[] {
  return activities
    .filter((a) => a.latitude != null && a.longitude != null)
    .map((a) => ({
      id: a.id,
      titre: a.titre,
      prix: a.prix,
      localisation: a.localisation,
      latitude: a.latitude as number,
      longitude: a.longitude as number,
    }));
}

/** Catalogue — rendu côté serveur pour chaque combinaison de filtres (SEO). */
export default async function ActivitiesPage({ searchParams }: { searchParams: SearchParams }) {
  const params = await searchParams;
  const search = first(params.search) ?? "";
  const catParam = first(params.cat);
  const cityParam = first(params.city) ?? "";
  const sort = first(params.sort) ?? "pop";
  const view = first(params.view) === "map" ? "map" : "grid";

  const [data, categories, all] = await Promise.all([
    fetchActivities({
      search: search || undefined,
      category_id: catParam ? Number(catParam) : undefined,
    }),
    fetchCategories(),
    // Catalogue complet : sert à alimenter la liste des villes du filtre, qui
    // ne doit pas se réduire à mesure que l'utilisateur filtre.
    fetchActivities({}),
  ]);

  const cities = [...new Set(all.items.map((a) => a.localisation).filter(Boolean))].sort((a, b) =>
    a.localeCompare(b, "fr"),
  );

  let items = [...data.items];
  // Le filtre ville est appliqué ici : le catalogue n'expose pas de paramètre
  // dédié, et la liste tient largement en mémoire à cette échelle.
  if (cityParam) {
    items = items.filter((a) => a.localisation === cityParam);
  }
  if (sort === "asc") items.sort((a, b) => a.prix - b.prix);
  else if (sort === "desc") items.sort((a, b) => b.prix - a.prix);

  const stats = await fetchReviewStats(items.map((a) => a.id));

  const points = view === "map" ? mapPoints(items) : [];

  return (
    <main className="mx-auto max-w-7xl px-4 py-10 sm:px-8">
      <div className="flex flex-wrap items-baseline justify-between gap-4">
        <div>
          <h1 className="font-display text-primary-hover text-4xl">
            <T k="nav.activities" />
          </h1>
          {/* Filet doré : rappel du zellige, marque le titre sans lourdeur. */}
          <div aria-hidden className="bg-gold mt-2 h-px w-14" />
          <p className="text-muted-foreground mt-2">
            <T k="catalog.results" values={{ count: items.length }} />
          </p>
        </div>
        <Suspense fallback={null}>
          <CatalogControls categories={categories} cities={cities} />
        </Suspense>
      </div>

      {view === "grid" ? (
        items.length === 0 ? (
          <div className="border-input bg-card rounded-2xl border border-dashed px-5 py-16 text-center">
            {/* Losange zellige : signale l'absence de résultat sans illustration. */}
            <div
              aria-hidden
              className="border-gold-ink/50 mx-auto mb-5 size-3.5 rotate-45 rounded-[3px] border-2"
            />
            <div className="font-display text-primary-hover mb-2 text-2xl">
              <T k="catalog.emptyTitle" />
            </div>
            <div className="text-muted-foreground mb-5">
              <T k="catalog.emptySub" />
            </div>
            <Link
              href="/activities"
              className="bg-primary text-primary-foreground hover:bg-primary-hover inline-block rounded-full px-6 py-3 font-semibold transition-colors"
            >
              <T k="catalog.reset" />
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-[repeat(auto-fill,minmax(280px,1fr))] gap-5">
            {items.map((activity) => (
              <ActivityCard
                key={activity.id}
                activity={activity}
                rating={stats[String(activity.id)]}
              />
            ))}
          </div>
        )
      ) : (
        <div className="border-border relative h-[560px] overflow-hidden rounded-3xl border">
          {points.length === 0 ? (
            <div className="from-background to-secondary text-muted-foreground flex size-full items-center justify-center bg-gradient-to-br px-6 text-center">
              <T k="catalog.mapEmpty" />
            </div>
          ) : (
            <>
              <ActivityMapLoader points={points} linkToActivity className="size-full" />
              <div className="bg-card/90 text-foreground/70 pointer-events-none absolute start-4 bottom-4 z-[500] rounded-xl px-4 py-2.5 text-[13px] shadow-md">
                <T k="catalog.mapHint" />
              </div>
            </>
          )}
        </div>
      )}
    </main>
  );
}
