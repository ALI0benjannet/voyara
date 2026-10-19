import type { Metadata } from "next";
import { Plane } from "lucide-react";

import { T } from "@/components/i18n/T";
import { FlightCard } from "@/components/offres/OffreCards";
import { OffresLayout } from "@/components/offres/OffresLayout";
import { fetchFlights } from "@/lib/server-api";

export const metadata: Metadata = {
  title: "Vols",
  description:
    "Vols directs vers et depuis la Tunisie : Tunis, Djerba, Monastir, Enfidha et Tozeur, au départ de Paris, Lyon, Marseille, Nice, Rome, Francfort, Bruxelles et Genève.",
  alternates: { canonical: "/flights" },
};

type SearchParams = Promise<Record<string, string | string[] | undefined>>;
const first = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v);

const AEROPORTS: [string, string][] = [
  ["TUN", "Tunis"],
  ["DJE", "Djerba"],
  ["MIR", "Monastir"],
  ["NBE", "Enfidha"],
  ["TOE", "Tozeur"],
  ["ORY", "Paris-Orly"],
  ["CDG", "Paris-CDG"],
  ["LYS", "Lyon"],
  ["MRS", "Marseille"],
  ["NCE", "Nice"],
  ["FCO", "Rome"],
  ["FRA", "Francfort"],
  ["BRU", "Bruxelles"],
  ["GVA", "Genève"],
];
const IATA = new Set(AEROPORTS.map(([code]) => code));
const iata = (v?: string) => (v && IATA.has(v) ? v : undefined);
const jourValide = (v?: string) => (v && /^\d{4}-\d{2}-\d{2}$/.test(v) ? v : undefined);

const FIELD =
  "border-input bg-card focus-visible:ring-primary h-10 rounded-lg border px-3 text-sm focus-visible:ring-2 focus-visible:outline-none";

/** Vols — formulaire GET (fonctionne sans JavaScript), résultats rendus côté serveur. */
export default async function FlightsPage({ searchParams }: { searchParams: SearchParams }) {
  const params = await searchParams;
  const depart = iata(first(params.depart));
  const arrivee = iata(first(params.arrivee));
  const jour = jourValide(first(params.jour));
  const flights = await fetchFlights({ depart, arrivee, jour });

  const select = (name: string, value: string | undefined, labelKey: string) => (
    <label className="flex flex-col gap-1 text-sm font-semibold">
      <T k={labelKey} />
      <select name={name} defaultValue={value ?? ""} className={FIELD}>
        <option value="">—</option>
        {AEROPORTS.map(([code, ville]) => (
          <option key={code} value={code}>
            {ville} ({code})
          </option>
        ))}
      </select>
    </label>
  );

  return (
    <OffresLayout
      icon={Plane}
      titleKey="nav.flights"
      subKey="comingSoon.flights"
      count={flights.length}
      basePath="/flights"
      filters={
        <form action="/flights" className="flex flex-wrap items-end gap-3">
          {select("depart", depart, "offres.from")}
          {select("arrivee", arrivee, "offres.to")}
          <label className="flex flex-col gap-1 text-sm font-semibold">
            <T k="offres.date" />
            <input type="date" name="jour" defaultValue={jour} className={FIELD} />
          </label>
          <button
            type="submit"
            className="bg-primary text-primary-foreground hover:bg-primary-hover h-10 rounded-lg px-5 text-sm font-semibold transition-colors"
          >
            <T k="offres.search" />
          </button>
          <p className="text-muted-foreground basis-full text-xs">
            <T k="offres.flightsHint" />
          </p>
        </form>
      }
    >
      <div className="flex flex-col gap-3">
        {flights.map((flight) => (
          <FlightCard key={flight.id} flight={flight} />
        ))}
      </div>
    </OffresLayout>
  );
}
