import type { Metadata } from "next";
import { Car } from "lucide-react";

import { CarCard } from "@/components/offres/OffreCards";
import { FilterChips, OffresLayout } from "@/components/offres/OffresLayout";
import { fetchCarRentals } from "@/lib/server-api";

export const metadata: Metadata = {
  title: "Location de voitures",
  description:
    "Louez une voiture en Tunisie : citadines, compactes, SUV et vans, à l'aéroport ou en ville.",
  alternates: { canonical: "/car-rentals" },
};

type SearchParams = Promise<Record<string, string | string[] | undefined>>;
const first = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v);

const VILLES = ["Tunis", "Djerba", "Monastir", "Sousse", "Enfidha", "Hammamet", "Tozeur"];
const CATEGORIES = ["economique", "compacte", "suv", "van"];

export default async function CarRentalsPage({ searchParams }: { searchParams: SearchParams }) {
  const params = await searchParams;
  const ville = first(params.ville);
  const categorie = first(params.categorie);
  const cars = await fetchCarRentals({ ville, categorie });
  const actifs = { ville, categorie };

  return (
    <OffresLayout
      icon={Car}
      titleKey="nav.carRentals"
      subKey="comingSoon.carRentals"
      count={cars.length}
      basePath="/car-rentals"
      filters={
        <>
          <FilterChips
            labelKey="offres.city"
            param="ville"
            options={VILLES.map((v) => ({ value: v, label: v }))}
            current={ville}
            basePath="/car-rentals"
            params={actifs}
          />
          <FilterChips
            labelKey="offres.category"
            param="categorie"
            options={CATEGORIES.map((v) => ({ value: v, labelKey: `admin.travel.options.${v}` }))}
            current={categorie}
            basePath="/car-rentals"
            params={actifs}
          />
        </>
      }
    >
      <div className="grid grid-cols-[repeat(auto-fill,minmax(260px,1fr))] gap-5">
        {cars.map((car) => (
          <CarCard key={car.id} car={car} />
        ))}
      </div>
    </OffresLayout>
  );
}
