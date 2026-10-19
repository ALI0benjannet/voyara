import type { Metadata } from "next";
import { BedDouble } from "lucide-react";

import { StayCard } from "@/components/offres/OffreCards";
import { FilterChips, OffresLayout } from "@/components/offres/OffresLayout";
import { fetchStays } from "@/lib/server-api";

export const metadata: Metadata = {
  title: "Séjours",
  description:
    "Hôtels, maisons d'hôtes et appartements en Tunisie : Djerba, Tunis, Sidi Bou Saïd, Sousse, Monastir, Hammamet et Tozeur.",
  alternates: { canonical: "/stays" },
};

type SearchParams = Promise<Record<string, string | string[] | undefined>>;
const first = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v);

const VILLES = ["Djerba", "Tunis", "Sousse", "Monastir", "Hammamet", "Tozeur"];
const TYPES = ["hotel", "maison_hotes", "appartement"];

/** Séjours — rendu côté serveur pour chaque combinaison de filtres (SEO). */
export default async function StaysPage({ searchParams }: { searchParams: SearchParams }) {
  const params = await searchParams;
  const ville = first(params.ville);
  const type = first(params.type);
  const stays = await fetchStays({ ville, type });
  const actifs = { ville, type };

  return (
    <OffresLayout
      icon={BedDouble}
      titleKey="nav.stays"
      subKey="comingSoon.stays"
      count={stays.length}
      basePath="/stays"
      filters={
        <>
          <FilterChips
            labelKey="offres.city"
            param="ville"
            options={VILLES.map((v) => ({ value: v, label: v }))}
            current={ville}
            basePath="/stays"
            params={actifs}
          />
          <FilterChips
            labelKey="offres.type"
            param="type"
            options={TYPES.map((v) => ({ value: v, labelKey: `admin.travel.options.${v}` }))}
            current={type}
            basePath="/stays"
            params={actifs}
          />
        </>
      }
    >
      <div className="grid grid-cols-[repeat(auto-fill,minmax(280px,1fr))] gap-5">
        {stays.map((stay) => (
          <StayCard key={stay.id} stay={stay} />
        ))}
      </div>
    </OffresLayout>
  );
}
