"use client";

import { ArrowRight, Briefcase, Clock, Fuel, Plane, Settings2, Users } from "lucide-react";

import { ActivityImage } from "@/components/activities/ActivityImage";
import { BookSoonBadge } from "@/components/offres/OffresLayout";
import { formatDuration, formatPrice } from "@/features/catalog/format";
import {
  stayDescription,
  stayName,
  type CarRental,
  type Flight,
  type Stay,
  type Transfer,
} from "@/features/offres/api";
import { useHydratedTranslation } from "@/features/i18n/use-hydrated-language";

/**
 * Cartes des offres de voyage. Les libellés d'interface passent par i18next ;
 * le contenu métier (nom et description des séjours) est lu en base dans la
 * langue active, avec repli français. Les types (hôtel, SUV, berline…)
 * réutilisent les libellés `admin.travel.options.*`, déjà traduits.
 */

const CARD = "card-elevated border-border bg-card flex flex-col overflow-hidden rounded-2xl border";

function Price({ value, unitKey }: { value: number; unitKey: string }) {
  const { t } = useHydratedTranslation();
  return (
    <div>
      <span className="text-lg font-bold">{formatPrice(value)}</span>
      <span className="text-muted-foreground text-xs"> {t(unitKey)}</span>
    </div>
  );
}

export function StayCard({ stay }: { stay: Stay }) {
  const { t, language: lang } = useHydratedTranslation();
  const name = stayName(stay, lang);
  const equipements = (stay.equipements ?? "").split(",").filter(Boolean).slice(0, 4);

  return (
    <article className={CARD}>
      <div className="relative h-44">
        <ActivityImage src={stay.photos} label={name} />
        <span className="bg-accent/95 text-accent-foreground absolute start-3 bottom-3 rounded-full px-3 py-1 text-xs font-semibold shadow-sm">
          {t(`admin.travel.options.${stay.type}`)}
        </span>
        {stay.etoiles && (
          <span
            className="bg-card/90 text-gold-ink absolute end-3 top-3 rounded-full px-2.5 py-1 text-xs font-bold"
            aria-label={t("offres.stars", { count: stay.etoiles })}
          >
            {"★".repeat(stay.etoiles)}
          </span>
        )}
      </div>
      <div className="flex flex-1 flex-col gap-1.5 p-4">
        <h3 className="font-display text-foreground text-lg leading-snug">{name}</h3>
        <div className="text-muted-foreground text-[13px]">{stay.localisation}</div>
        <p className="text-foreground/75 line-clamp-3 text-[13px]">{stayDescription(stay, lang)}</p>
        <div className="text-muted-foreground flex items-center gap-1.5 text-[13px]">
          <Users className="size-3.5" /> {t("offres.guests", { count: stay.capacite })}
        </div>
        {equipements.length > 0 && (
          <div className="flex flex-wrap gap-1.5 pt-1">
            {equipements.map((e) => (
              <span
                key={e}
                className="bg-secondary text-foreground/70 rounded-md px-2 py-0.5 text-[11px]"
              >
                {e}
              </span>
            ))}
          </div>
        )}
        <div className="mt-auto flex items-center justify-between gap-2 pt-3">
          <Price value={stay.prix_nuit} unitKey="offres.perNight" />
          <BookSoonBadge />
        </div>
      </div>
    </article>
  );
}

export function CarCard({ car }: { car: CarRental }) {
  const { t } = useHydratedTranslation();
  return (
    <article className={CARD}>
      <div className="relative h-40 bg-white">
        <ActivityImage src={car.photos} label={`${car.marque} ${car.modele}`} />
        <span className="bg-accent/95 text-accent-foreground absolute start-3 bottom-3 rounded-full px-3 py-1 text-xs font-semibold shadow-sm">
          {t(`admin.travel.options.${car.categorie}`)}
        </span>
      </div>
      <div className="flex flex-1 flex-col gap-1.5 p-4">
        <h3 className="font-display text-foreground text-lg leading-snug">
          {car.marque} {car.modele}
        </h3>
        <div className="text-muted-foreground text-[13px]">
          {t("offres.pickup")} : {car.localisation}
        </div>
        <div className="text-foreground/75 flex flex-wrap gap-x-4 gap-y-1 text-[13px]">
          <span className="inline-flex items-center gap-1.5">
            <Users className="size-3.5" /> {t("offres.seats", { count: car.nb_places })}
          </span>
          <span className="inline-flex items-center gap-1.5">
            <Settings2 className="size-3.5" /> {t(`admin.travel.options.${car.transmission}`)}
          </span>
          <span className="inline-flex items-center gap-1.5">
            <Fuel className="size-3.5" /> {t(`admin.travel.options.${car.carburant}`)}
          </span>
        </div>
        <div className="text-muted-foreground text-[12px]">{car.agence}</div>
        <div className="mt-auto flex items-center justify-between gap-2 pt-3">
          <Price value={car.prix_jour} unitKey="offres.perDay" />
          <BookSoonBadge />
        </div>
      </div>
    </article>
  );
}

export function TransferCard({ transfer }: { transfer: Transfer }) {
  const { t, language: lang } = useHydratedTranslation();
  return (
    <article className={`${CARD} p-4`}>
      <div className="mb-2 flex items-center justify-between gap-2">
        <span className="bg-accent/95 text-accent-foreground rounded-full px-3 py-1 text-xs font-semibold">
          {t(`admin.travel.options.${transfer.type_vehicule}`)}
        </span>
        <span className="text-muted-foreground inline-flex items-center gap-1.5 text-[13px]">
          <Clock className="size-3.5" /> {formatDuration(transfer.duree, lang)}
        </span>
      </div>
      <h3 className="font-display text-foreground flex flex-wrap items-center gap-2 text-lg leading-snug">
        {transfer.depart}
        <ArrowRight className="text-primary size-4 shrink-0 rtl:rotate-180" />
        {transfer.arrivee}
      </h3>
      <div className="text-foreground/75 mt-1 flex flex-wrap gap-x-4 gap-y-1 text-[13px]">
        <span className="inline-flex items-center gap-1.5">
          <Users className="size-3.5" /> {t("offres.seats", { count: transfer.capacite })}
        </span>
        <span className="inline-flex items-center gap-1.5">
          <Briefcase className="size-3.5" /> {t("offres.bags", { count: transfer.bagages })}
        </span>
      </div>
      {transfer.description && (
        <p className="text-muted-foreground mt-2 text-[13px]">{transfer.description}</p>
      )}
      <div className="mt-auto flex items-center justify-between gap-2 pt-3">
        <Price value={transfer.prix} unitKey="offres.perVehicle" />
        <BookSoonBadge />
      </div>
    </article>
  );
}

/** « 2026-10-20T07:00:00 » → date et heure locales de l'aéroport, sans
 *  conversion de fuseau (le catalogue stocke l'heure locale de chaque aéroport). */
function splitLocal(iso: string, lang: string) {
  const [d, time] = iso.split("T");
  const [y, m, day] = d.split("-").map(Number);
  const locale = lang === "ar" ? "ar-TN" : lang === "en" ? "en-GB" : "fr-FR";
  const date = new Intl.DateTimeFormat(locale, {
    weekday: "short",
    day: "numeric",
    month: "short",
  }).format(new Date(y, m - 1, day));
  return { date, heure: time.slice(0, 5) };
}

export function FlightCard({ flight }: { flight: Flight }) {
  const { t, language: lang } = useHydratedTranslation();
  const dep = splitLocal(flight.depart_le, lang);
  const arr = splitLocal(flight.arrivee_le, lang);
  const peu = flight.places_disponibles <= 10;

  return (
    <article className="card-elevated border-border bg-card flex flex-wrap items-center gap-x-6 gap-y-3 rounded-2xl border p-4">
      <div className="flex min-w-36 items-center gap-3">
        <div className="bg-primary/10 text-primary flex size-10 items-center justify-center rounded-lg">
          <Plane className="size-5 rtl:-scale-x-100" />
        </div>
        <div>
          <div className="font-semibold">{flight.compagnie}</div>
          <div className="text-muted-foreground text-[12px]">
            {flight.numero_vol} · {t(`admin.travel.options.${flight.classe}`)}
          </div>
        </div>
      </div>

      <div className="flex flex-1 items-center gap-4">
        <div className="text-center">
          <div className="text-xl font-bold">{dep.heure}</div>
          <div className="text-[13px] font-semibold">{flight.aeroport_depart}</div>
          <div className="text-muted-foreground text-[12px]">{flight.ville_depart}</div>
        </div>
        <div className="text-muted-foreground flex flex-1 flex-col items-center text-[11px]">
          <span>{dep.date}</span>
          <div className="bg-border my-1 h-px w-full" />
          <span>{t("offres.direct")}</span>
        </div>
        <div className="text-center">
          <div className="text-xl font-bold">{arr.heure}</div>
          <div className="text-[13px] font-semibold">{flight.aeroport_arrivee}</div>
          <div className="text-muted-foreground text-[12px]">{flight.ville_arrivee}</div>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className="text-end">
          <Price value={flight.prix} unitKey="catalog.perPerson" />
          <div
            className={`text-[12px] ${peu ? "font-semibold text-red-600" : "text-muted-foreground"}`}
          >
            {t("offres.seatsLeft", { count: flight.places_disponibles })}
          </div>
        </div>
        <BookSoonBadge />
      </div>
    </article>
  );
}
