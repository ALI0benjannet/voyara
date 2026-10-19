import type { Metadata } from "next";
import Link from "next/link";
import Image, { type StaticImageData } from "next/image";
import { ArrowRight, BedDouble, Car, CarTaxiFront, Plane, type LucideIcon } from "lucide-react";
import fr from "@voyara/i18n/locales/fr/common.json";

import { ActivityCard } from "@/components/activities/ActivityCard";
import { T } from "@/components/i18n/T";
import { AiTripPlanner } from "@/components/home/AiTripPlanner";
import { CategoryTiles, type CategoryTile } from "@/components/home/CategoryTiles";
import { StayCard } from "@/components/offres/OffreCards";
import type { Activity } from "@/features/catalog/api";
import { formatPrice } from "@/features/catalog/format";
import type { Stay } from "@/features/offres/api";
import {
  fetchAllActivities,
  fetchCarRentals,
  fetchCategories,
  fetchFlights,
  fetchReviewStats,
  fetchStays,
  fetchTransfers,
  type ReviewStat,
} from "@/lib/server-api";
import { paths } from "@/routes/paths";
import couverture from "@/assets/couv.png";
import djerba from "@/assets/Djerba.png";
import tozeur from "@/assets/Touzeur&ledesert.png";
import tunis from "@/assets/Tunis&Carthage.png";

export const metadata: Metadata = {
  description: fr.home.heroSub,
  alternates: { canonical: "/" },
};

/* Régions mises en avant — uniquement celles où le catalogue a des offres
 * (Tabarka a été retirée : aucune activité ni séjour, la carte menait à une
 * page vide). `q` filtre le catalogue ; `prefix` compte les offres de la région. */
const DESTINATIONS: {
  name: string;
  q: string;
  prefixes: string[];
  tagKey: string;
  image: StaticImageData | string;
}[] = [
  {
    name: "Tunis & Carthage",
    q: "Tunis",
    prefixes: ["Tunis"],
    tagKey: "home.destTags.tunis",
    image: tunis,
  },
  {
    name: "Djerba",
    q: "Djerba",
    prefixes: ["Djerba"],
    tagKey: "home.destTags.djerba",
    image: djerba,
  },
  {
    name: "Tozeur & le désert",
    q: "Tozeur",
    prefixes: ["Tozeur"],
    tagKey: "home.destTags.tozeur",
    image: tozeur,
  },
  {
    name: "Hammamet",
    q: "Hammamet",
    prefixes: ["Hammamet"],
    tagKey: "home.destTags.hammamet",
    image: "/static/activities/demo/medina-et-kasbah-de-hammamet.jpg",
  },
];

const VALUE_KEYS = ["home.values.cancel", "home.values.guides", "home.values.payment"];

const startsWithAny = (value: string, prefixes: string[]) =>
  prefixes.some((p) => value.toLowerCase().startsWith(p.toLowerCase()));

/** Les mieux notées d'abord (moyenne pondérée par le nombre d'avis), puis une
 *  activité par catégorie pour compléter : la sélection reste variée même tant
 *  que peu d'avis existent. */
function popularActivities(
  activities: Activity[],
  stats: Record<string, ReviewStat>,
  count: number,
): Activity[] {
  const score = (a: Activity) => {
    const s = stats[String(a.id)];
    return s && s.count > 0 ? s.average * Math.log1p(s.count) : 0;
  };
  const rated = activities.filter((a) => score(a) > 0).sort((a, b) => score(b) - score(a));
  const picked = rated.slice(0, count);
  const seen = new Set(picked.map((a) => a.category_id));
  for (const a of activities) {
    if (picked.length >= count) break;
    if (!a.photos || picked.includes(a) || seen.has(a.category_id)) continue;
    picked.push(a);
    seen.add(a.category_id);
  }
  for (const a of activities) {
    if (picked.length >= count) break;
    if (a.photos && !picked.includes(a)) picked.push(a);
  }
  return picked;
}

/** Un séjour par région, du moins cher au plus cher : variété géographique. */
function featuredStays(stays: Stay[], count: number): Stay[] {
  const byCity = new Map<string, Stay>();
  for (const s of stays) {
    const city = s.localisation.split(",")[0]!.trim();
    if (!byCity.has(city) && s.photos) byCity.set(city, s);
  }
  return [...byCity.values()].slice(0, count);
}

const minOf = (values: number[]) => (values.length ? Math.min(...values) : 0);

/** Page d'accueil — rendue côté serveur (SEO) ; recherche et cœurs = îlots client. */
export default async function HomePage() {
  const [activities, categories, stays, flights, cars, transfers] = await Promise.all([
    fetchAllActivities(),
    fetchCategories(),
    fetchStays({}),
    fetchFlights({ limite: "1000" }),
    fetchCarRentals({}),
    fetchTransfers({}),
  ]);
  const stats = await fetchReviewStats(activities.map((a) => a.id));
  const popular = popularActivities(activities, stats, 8);

  const categoryTiles: CategoryTile[] = categories
    .map((category) => {
      const inCategory = activities.filter((a) => a.category_id === category.id);
      return {
        category,
        count: inCategory.length,
        photo: inCategory.find((a) => a.photos)?.photos ?? null,
      };
    })
    .filter((tile) => tile.count > 0)
    .sort((a, b) => b.count - a.count);

  const offerTiles: {
    href: string;
    titleKey: string;
    Icon: LucideIcon;
    subKey: string;
    values: Record<string, unknown>;
  }[] = [
    {
      href: paths.stays,
      titleKey: "nav.stays",
      Icon: BedDouble,
      subKey: "home.staysFrom",
      values: { price: formatPrice(minOf(stays.map((s) => s.prix_nuit))) },
    },
    {
      href: paths.flights,
      titleKey: "nav.flights",
      Icon: Plane,
      subKey: "home.flightsCount",
      values: { count: flights.length },
    },
    {
      href: paths.carRentals,
      titleKey: "nav.carRentals",
      Icon: Car,
      subKey: "home.carsFrom",
      values: { price: formatPrice(minOf(cars.map((c) => c.prix_jour))) },
    },
    {
      href: paths.transfers,
      titleKey: "nav.transfers",
      Icon: CarTaxiFront,
      subKey: "home.transfersFrom",
      values: { price: formatPrice(minOf(transfers.map((t) => t.prix))) },
    },
  ];

  const sectionTitle = (titleKey: string, subKey: string) => (
    <div className="mb-8 text-center">
      <h2 className="font-display text-primary-hover text-4xl">
        <T k={titleKey} />
      </h2>
      {/* Séparateur zellige : signature visuelle discrète entre titre et sous-titre. */}
      <div aria-hidden className="zellige-divider mx-auto mt-1 max-w-xs" />
      <p className="text-muted-foreground mt-1">
        <T k={subKey} />
      </p>
    </div>
  );

  const seeAll = (href: string, labelKey: string) => (
    <div className="mt-8 text-center">
      <Link
        href={href}
        className="border-input hover:border-primary hover:bg-primary/5 hover:text-primary focus-visible:ring-primary inline-flex items-center gap-2 rounded-full border px-5 py-2.5 text-sm font-semibold transition-colors focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none"
      >
        <T k={labelKey} />
        <ArrowRight className="size-4 rtl:rotate-180" />
      </Link>
    </div>
  );

  return (
    <div>
      {/* ---- Hero + agent IA ---- */}
      <section className="relative overflow-hidden">
        <Image
          src={couverture}
          alt="Couverture - Méditerranée"
          priority
          className="absolute inset-0 h-full w-full object-cover object-bottom"
        />
        {/* Voile dégradé plutôt qu'un noir uniforme : la photo reste lisible
            en haut, le texte gagne le contraste dont il a besoin en bas. */}
        <div className="from-ink/70 via-ink/45 to-ink/65 absolute inset-0 bg-gradient-to-b" />
        {/* Zellige en filigrane — texture, jamais un élément à lire. */}
        <div aria-hidden className="zellige-pattern absolute inset-0 opacity-[0.07]" />

        <div className="animate-fade-up relative mx-auto max-w-7xl px-4 pt-14 pb-16 text-center sm:px-8">
          {/* Or vif : 10:1 sur ce fond sombre — le contexte où il est le plus juste. */}
          <span className="border-gold/40 bg-ink/25 text-gold inline-flex items-center gap-2.5 rounded-full border px-4 py-1.5 text-[13px] font-semibold tracking-[0.14em] uppercase backdrop-blur-sm">
            <span aria-hidden className="text-base leading-none">
              ✦
            </span>
            <T k="home.heroKicker" />
          </span>
          <h1 className="font-display mx-auto mt-7 mb-8 w-full text-center text-4xl leading-[1.08] text-white drop-shadow-[0_2px_12px_rgba(22,48,60,0.45)] sm:text-7xl sm:whitespace-nowrap">
            <T k="home.heroTitle" />
          </h1>
          <p className="mx-auto mb-7 w-full text-center text-lg leading-relaxed font-normal tracking-wide text-white/95 sm:whitespace-nowrap">
            <T k="home.aiPlanner.sub" />
          </p>
          {/* L'agent IA est l'entrée principale du site ; la recherche par mot-clé
              reste disponible dans l'en-tête. */}
          <AiTripPlanner />
        </div>
      </section>

      {/* ---- Tout le voyage : raccourcis vers les 4 offres, avec un chiffre réel ---- */}
      <section className="relative z-10 mx-auto -mt-8 max-w-7xl px-4 sm:px-8">
        <h2 className="sr-only">
          <T k="home.offersTitle" />
        </h2>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {offerTiles.map(({ href, titleKey, Icon, subKey, values }) => (
            <Link
              key={href}
              href={href}
              className="card-elevated group border-border bg-card focus-visible:ring-primary flex items-center gap-3 rounded-2xl border p-4 transition-all hover:-translate-y-0.5 focus-visible:ring-2 focus-visible:outline-none"
            >
              <span className="bg-primary/10 text-primary group-hover:bg-primary group-hover:text-primary-foreground flex size-11 shrink-0 items-center justify-center rounded-xl transition-colors">
                <Icon className="size-5" strokeWidth={1.7} />
              </span>
              <span className="min-w-0">
                <span className="block font-semibold">
                  <T k={titleKey} />
                </span>
                <span className="text-muted-foreground block truncate text-[13px]">
                  <T k={subKey} values={values} />
                </span>
              </span>
            </Link>
          ))}
        </div>
      </section>

      {/* ---- Destinations ---- */}
      <section className="mx-auto max-w-7xl px-4 pt-18 pb-14 sm:px-8">
        {sectionTitle("home.destTitle", "home.destSub")}
        <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-4">
          {DESTINATIONS.map((dest) => {
            const nbActivities = activities.filter((a) =>
              startsWithAny(a.localisation, dest.prefixes),
            ).length;
            const nbStays = stays.filter((s) =>
              startsWithAny(s.localisation, dest.prefixes),
            ).length;
            return (
              <Link
                key={dest.name}
                href={`${paths.activities}?search=${encodeURIComponent(dest.q)}`}
                className="group focus-visible:ring-primary relative block h-[360px] overflow-hidden rounded-2xl transition-all duration-300 hover:-translate-y-1 focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none"
                style={{ boxShadow: "var(--shadow-card)" }}
              >
                {typeof dest.image === "string" ? (
                  // Photo du catalogue (servie par le gateway) : pas d'import statique possible.
                  <img
                    src={dest.image}
                    alt={dest.name}
                    loading="lazy"
                    decoding="async"
                    className="absolute inset-0 size-full object-cover object-center transition-transform duration-500 group-hover:scale-105"
                  />
                ) : (
                  <Image
                    src={dest.image}
                    alt={dest.name}
                    fill
                    sizes="(min-width: 1280px) 25vw, (min-width: 768px) 50vw, 100vw"
                    className="object-cover object-center transition-transform duration-500 group-hover:scale-105"
                  />
                )}

                {/* Voile à l'encre de la palette, plutôt qu'un vert isolé. */}
                <div className="from-ink/80 via-ink/20 group-hover:from-ink/85 absolute inset-0 bg-gradient-to-t to-transparent transition-opacity duration-300" />

                <div className="pointer-events-none absolute inset-x-0 bottom-0 px-5 pt-10 pb-5 text-white">
                  <div className="font-display text-3xl leading-tight">{dest.name}</div>
                  {/* Filet doré : rappel du zellige, s'étire au survol. */}
                  <div
                    aria-hidden
                    className="bg-gold mt-2 h-px w-10 transition-all duration-300 group-hover:w-20"
                  />
                  <div className="mt-2 text-base text-white/90">
                    <T k={dest.tagKey} />
                  </div>
                  <div className="mt-1 text-[13px] text-white/75">
                    <T k="home.destCount" values={{ activities: nbActivities, stays: nbStays }} />
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      </section>

      {/* ---- Explorer par envie (catégories) ---- */}
      {categoryTiles.length > 0 && (
        <section className="mx-auto max-w-7xl px-4 pt-6 pb-14 sm:px-8">
          {sectionTitle("home.catTitle", "home.catSub")}
          <CategoryTiles tiles={categoryTiles} />
        </section>
      )}

      {/* ---- Activités populaires ---- */}
      <section className="mx-auto max-w-7xl px-4 pt-6 pb-14 sm:px-8">
        {sectionTitle("home.popTitle", "home.popSub")}
        <div className="grid grid-cols-[repeat(auto-fill,minmax(260px,1fr))] gap-5">
          {popular.map((activity) => (
            <ActivityCard
              key={activity.id}
              activity={activity}
              rating={stats[String(activity.id)]}
            />
          ))}
        </div>
        {seeAll(paths.activities, "home.seeAll")}
      </section>

      {/* ---- Séjours coups de cœur ---- */}
      {stays.length > 0 && (
        <section className="mx-auto max-w-7xl px-4 pt-6 pb-16 sm:px-8">
          {sectionTitle("home.staysTitle", "home.staysSub")}
          <div className="grid grid-cols-[repeat(auto-fill,minmax(260px,1fr))] gap-5">
            {featuredStays(stays, 4).map((stay) => (
              <StayCard key={stay.id} stay={stay} />
            ))}
          </div>
          {seeAll(paths.stays, "home.seeAllStays")}
        </section>
      )}

      {/* ---- Arguments ---- */}
      <section className="bg-secondary/60 relative overflow-hidden py-14">
        {/* Bande sable texturée : marque la fin de page sans ajouter d'image. */}
        <div aria-hidden className="zellige-pattern absolute inset-0 opacity-[0.05]" />
        <div className="relative mx-auto max-w-7xl px-4 sm:px-8">
          <div className="grid gap-5 sm:grid-cols-3">
            {VALUE_KEYS.map((key) => (
              <div
                key={key}
                className="card-elevated border-border bg-card rounded-2xl border p-7 text-center"
              >
                {/* Losange doré : motif zellige réduit à sa forme la plus simple. */}
                <div
                  aria-hidden
                  className="bg-gold mx-auto mb-4 size-2.5 rotate-45 rounded-[2px]"
                />
                <div className="font-display text-primary-hover mb-2 text-lg">
                  <T k={`${key}.title`} />
                </div>
                <div className="text-muted-foreground text-sm leading-relaxed">
                  <T k={`${key}.body`} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
