import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import fr from "@voyara/i18n/locales/fr/common.json";

import { ActivityContent } from "@/components/activities/ActivityContent";
import { BackToActivities } from "@/components/activities/BackToActivities";
import { ActivityImage } from "@/components/activities/ActivityImage";
import { ActivityLocation } from "@/components/activities/ActivityLocation";
import { BookingCard } from "@/components/activities/BookingCard";
import { FavoriteButton } from "@/components/activities/FavoriteButton";
import { fetchActivities, fetchActivity, fetchReviewStats } from "@/lib/server-api";
import { SITE_URL } from "@/lib/site";

type Params = Promise<{ id: string }>;

/** Pré-génère les pages détail connues au build (ISR ensuite). */
export async function generateStaticParams() {
  const data = await fetchActivities({ size: 50 });
  return data.items.map((a) => ({ id: String(a.id) }));
}

export async function generateMetadata({ params }: { params: Params }): Promise<Metadata> {
  const { id } = await params;
  const activity = await fetchActivity(Number(id));
  if (!activity) return { title: "Activité introuvable" };

  const description = activity.description.slice(0, 160);
  return {
    title: activity.titre,
    description,
    alternates: { canonical: `/activities/${activity.id}` },
    openGraph: {
      title: activity.titre,
      description,
      type: "article",
      url: `${SITE_URL}/activities/${activity.id}`,
    },
  };
}

/** Page détail — rendue côté serveur (SEO + JSON-LD) ; réservation = îlot client. */
export default async function ActivityDetailPage({ params }: { params: Params }) {
  const { id } = await params;
  const activityId = Number(id);
  if (!Number.isFinite(activityId)) notFound();

  const activity = await fetchActivity(activityId);
  if (!activity) notFound();

  const stats = (await fetchReviewStats([activityId]))[String(activityId)];

  // Données structurées schema.org (produit touristique)
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "TouristAttraction",
    name: activity.titre,
    description: activity.description,
    url: `${SITE_URL}/activities/${activity.id}`,
    ...(activity.latitude != null && activity.longitude != null
      ? {
          geo: {
            "@type": "GeoCoordinates",
            latitude: activity.latitude,
            longitude: activity.longitude,
          },
        }
      : {}),
    address: {
      "@type": "PostalAddress",
      addressLocality: activity.localisation,
      addressCountry: "TN",
    },
    offers: {
      "@type": "Offer",
      price: activity.prix,
      priceCurrency: "TND",
      availability: "https://schema.org/InStock",
    },
    ...(stats && stats.count > 0
      ? {
          aggregateRating: {
            "@type": "AggregateRating",
            ratingValue: stats.average,
            reviewCount: stats.count,
          },
        }
      : {}),
  };

  return (
    <main className="mx-auto max-w-7xl px-4 py-9 sm:px-8">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      <BackToActivities />

      {/* Image principale — cadrage seul, le fichier n'est pas modifié. */}
      <div
        className="border-border relative h-72 overflow-hidden rounded-2xl border sm:h-96"
        style={{ boxShadow: "var(--shadow-card)" }}
      >
        <ActivityImage src={activity.photos} label={`Photo — ${activity.localisation}`} priority />
        {/* Dégradé bas : détache le cœur de la photo quelle qu'elle soit. */}
        <div
          aria-hidden
          className="from-ink/25 pointer-events-none absolute inset-x-0 bottom-0 h-24 bg-gradient-to-t to-transparent"
        />
        <FavoriteButton activityId={activity.id} size="lg" />
      </div>

      <div className="mt-8 grid items-start gap-9 lg:grid-cols-[1fr_380px]">
        {/* Contenu indexable */}
        <article>
          <ActivityContent activity={activity} stats={stats} />

          <ActivityLocation activity={activity} />
        </article>

        <BookingCard activityId={activity.id} prix={activity.prix} />
      </div>
    </main>
  );
}
