import type { Metadata } from "next";
import Link from "next/link";
import Image from "next/image";
import fr from "@voyara/i18n/locales/fr/common.json";

import { ActivityCard } from "@/components/activities/ActivityCard";
import { T } from "@/components/i18n/T";
import { AiTripPlanner } from "@/components/home/AiTripPlanner";
import { fetchActivities, fetchReviewStats } from "@/lib/server-api";
import { paths } from "@/routes/paths";
import couverture from "@/assets/couv.png";
import djerba from "@/assets/Djerba.png";
import tabarka from "@/assets/Tbarka.png";
import tozeur from "@/assets/Touzeur&ledesert.png";
import tunis from "@/assets/Tunis&Carthage.png";

export const metadata: Metadata = {
  description: fr.home.heroSub,
  alternates: { canonical: "/" },
};

/* Régions mises en avant (design) — mènent au catalogue filtré */
const DESTINATIONS = [
  {
    name: "Tunis & Carthage",
    q: "Tunis",
    tagKey: "home.destTags.tunis",
    image: tunis,
  },
  {
    name: "Djerba",
    q: "Djerba",
    tagKey: "home.destTags.djerba",
    image: djerba,
  },
  {
    name: "Tozeur & le désert",
    q: "Tozeur",
    tagKey: "home.destTags.tozeur",
    image: tozeur,
  },
  {
    name: "Tabarka",
    q: "Tabarka",
    tagKey: "home.destTags.tabarka",
    image: tabarka,
  },
] as const;

const VALUE_KEYS = ["home.values.cancel", "home.values.guides", "home.values.payment"];
/** Page d'accueil — rendue côté serveur (SEO) ; recherche et cœurs = îlots client. */
export default async function HomePage() {
  const popular = await fetchActivities({ size: 4 });
  const stats = await fetchReviewStats(popular.items.map((a) => a.id));
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

      {/* ---- Destinations ---- */}
      <section className="mx-auto max-w-7xl px-4 pt-18 pb-16 sm:px-8">
        <div className="mb-6 text-center">
          <h2 className="font-display text-primary-hover text-4xl">
            <T k="home.destTitle" />
          </h2>
          {/* Séparateur zellige : signature visuelle discrète entre le titre
              et son sous-titre, estompée sur les bords. */}
          <div aria-hidden className="zellige-divider mx-auto mt-1 max-w-xs" />
          <p className="text-muted-foreground mt-1">
            <T k="home.destSub" />
          </p>
        </div>

        <div className="grid grid-cols-1 gap-5 pt-8 md:grid-cols-2 xl:grid-cols-4">
          {DESTINATIONS.map((dest) => (
            <Link
              key={dest.name}
              href={`${paths.activities}?search=${encodeURIComponent(dest.q)}`}
              className="group focus-visible:ring-primary relative block h-[360px] overflow-hidden rounded-2xl transition-all duration-300 hover:-translate-y-1 focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none"
              style={{ boxShadow: "var(--shadow-card)" }}
            >
              <Image
                src={dest.image}
                alt={dest.name}
                fill
                className="object-cover object-center transition-transform duration-500 group-hover:scale-105"
              />

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
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* ---- Activités populaires ---- */}
      <section className="mx-auto max-w-7xl px-4 pt-14 pb-5 sm:px-8">
        <div className="mb-6 flex flex-col items-center text-center">
          <div>
            <h2 className="font-display text-primary-hover text-4xl">
              <T k="home.popTitle" />
            </h2>
            <div aria-hidden className="zellige-divider mx-auto mt-1 max-w-xs" />
            <p className="text-muted-foreground mt-1">
              <T k="home.popSub" />
            </p>
          </div>
          <Link
            href={paths.activities}
            className="border-input hover:border-primary hover:bg-primary/5 hover:text-primary focus-visible:ring-primary mt-4 rounded-full border px-5 py-2.5 text-sm font-semibold transition-colors focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none"
          >
            <T k="home.seeAll" />
          </Link>
        </div>
        <div className="grid grid-cols-[repeat(auto-fill,minmax(260px,1fr))] gap-5">
          {popular.items.map((activity) => (
            <ActivityCard
              key={activity.id}
              activity={activity}
              rating={stats[String(activity.id)]}
            />
          ))}
        </div>
      </section>

      {/* ---- Arguments ---- */}
      <section className="bg-secondary/60 relative mt-4 overflow-hidden py-14">
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
                {/* Purement décoratif (aucun texte) : l'or vif convient ici. */}
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
