import type { Metadata } from "next";
import { CarTaxiFront } from "lucide-react";

import { TransferCard } from "@/components/offres/OffreCards";
import { FilterChips, OffresLayout } from "@/components/offres/OffresLayout";
import { fetchTransfers } from "@/lib/server-api";

export const metadata: Metadata = {
  title: "Transferts",
  description:
    "Transferts avec chauffeur en Tunisie : aéroport de Tunis, Djerba, Monastir, Enfidha et Tozeur vers votre hôtel.",
  alternates: { canonical: "/transfers" },
};

type SearchParams = Promise<Record<string, string | string[] | undefined>>;
const first = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v);

/** Valeur = début du lieu de départ en base ; libellé = nom court de l'aéroport. */
const DEPARTS = [
  { value: "Aéroport Tunis", label: "Tunis-Carthage (TUN)" },
  { value: "Aéroport Djerba", label: "Djerba-Zarzis (DJE)" },
  { value: "Aéroport Monastir", label: "Monastir (MIR)" },
  { value: "Aéroport Enfidha", label: "Enfidha-Hammamet (NBE)" },
  { value: "Aéroport Tozeur", label: "Tozeur-Nefta (TOE)" },
];

export default async function TransfersPage({ searchParams }: { searchParams: SearchParams }) {
  const params = await searchParams;
  const depart = first(params.depart);
  const transfers = await fetchTransfers({ depart });

  return (
    <OffresLayout
      icon={CarTaxiFront}
      titleKey="nav.transfers"
      subKey="comingSoon.transfers"
      count={transfers.length}
      basePath="/transfers"
      filters={
        <FilterChips
          labelKey="offres.from"
          param="depart"
          options={DEPARTS}
          current={depart}
          basePath="/transfers"
          params={{ depart }}
        />
      }
    >
      <div className="grid grid-cols-[repeat(auto-fill,minmax(320px,1fr))] gap-5">
        {transfers.map((transfer) => (
          <TransferCard key={transfer.id} transfer={transfer} />
        ))}
      </div>
    </OffresLayout>
  );
}
